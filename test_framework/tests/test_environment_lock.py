"""
Test suite for environment_lock module.
"""

import pytest
import time
import threading
from pathlib import Path
from test_framework.environment_lock import (
from shared.isolated_environment import IsolatedEnvironment
    EnvironmentLock, 
    EnvironmentType, 
    LockStatus,
    LockAcquisitionTimeout,
    LockNotHeldError
)


class TestEnvironmentLock:
    """Test cases for EnvironmentLock class."""
    
    def test_basic_lock_acquisition(self, tmp_path):
        """Test basic lock acquisition and release."""
        lock = EnvironmentLock(lock_dir=tmp_path)
        
        # Acquire dev lock
        success = lock.acquire_dev(timeout=5, purpose="Test development")
        assert success
        
        # Check status
        status = lock.check_lock_status("dev")
        assert status.status == LockStatus.LOCKED
        assert status.metadata is not None
        assert status.metadata.environment == "dev"
        assert status.metadata.purpose == "Test development"
        
        # Release
        released = lock.release_all()
        assert "dev" in released
        
        # Check status after release
        status = lock.check_lock_status("dev")
        assert status.status == LockStatus.AVAILABLE
    
    def test_context_manager(self, tmp_path):
        """Test context manager functionality."""
    pass
        with EnvironmentLock(lock_dir=tmp_path) as lock:
            success = lock.acquire_test(timeout=5, purpose="Context manager test")
            assert success
            
            status = lock.check_lock_status("test")
            assert status.status == LockStatus.LOCKED
        
        # Should be released after context exit
        lock2 = EnvironmentLock(lock_dir=tmp_path)
        status = lock2.check_lock_status("test")
        assert status.status == LockStatus.AVAILABLE
    
    def test_concurrent_lock_conflict(self, tmp_path):
        """Test that concurrent locks conflict properly."""
        lock1 = EnvironmentLock(lock_dir=tmp_path)
        lock2 = EnvironmentLock(lock_dir=tmp_path)
        
        # First lock acquires successfully
        success1 = lock1.acquire_staging(timeout=2, purpose="First lock")
        assert success1
        
        # Second lock should timeout
        with pytest.raises(LockAcquisitionTimeout):
            lock2.acquire_staging(timeout=1, purpose="Second lock")
        
        # Release first lock
        lock1.release_all()
        
        # Now second lock should succeed
        success2 = lock2.acquire_staging(timeout=2, purpose="After release")
        assert success2
        
        lock2.release_all()
    
    def test_all_environment_types(self, tmp_path):
        """Test all environment type acquisitions."""
    pass
        lock = EnvironmentLock(lock_dir=tmp_path)
        
        # Test each environment type
        assert lock.acquire_dev(timeout=2, purpose="Dev test")
        assert lock.acquire_test(timeout=2, purpose="Test test") 
        assert lock.acquire_staging(timeout=2, purpose="Staging test")
        assert lock.acquire_production(timeout=2, purpose="Production test")
        
        # All should be locked
        for env_type in EnvironmentType:
            status = lock.check_lock_status(env_type.value)
            assert status.status == LockStatus.LOCKED
        
        # Release all
        released = lock.release_all()
        assert len(released) == 4
        
        # All should be available
        for env_type in EnvironmentType:
            status = lock.check_lock_status(env_type.value)
            assert status.status == LockStatus.AVAILABLE
    
    def test_force_release(self, tmp_path):
        """Test force release functionality."""
        lock1 = EnvironmentLock(lock_dir=tmp_path)
        lock2 = EnvironmentLock(lock_dir=tmp_path)
        
        # Lock1 acquires
        lock1.acquire_dev(timeout=2, purpose="To be force released")
        
        # Verify locked
        status = lock2.check_lock_status("dev")
        assert status.status == LockStatus.LOCKED
        
        # Force release from lock2
        success = lock2.force_release("dev", "Test force release")
        assert success
        
        # Should now be available
        status = lock2.check_lock_status("dev")
        assert status.status == LockStatus.AVAILABLE
    
    def test_not_held_error(self, tmp_path):
        """Test error when releasing lock not held."""
    pass
        lock = EnvironmentLock(lock_dir=tmp_path)
        
        with pytest.raises(LockNotHeldError):
            lock.release("dev")
    
    def test_list_all_locks(self, tmp_path):
        """Test listing all lock statuses."""
        lock = EnvironmentLock(lock_dir=tmp_path)
        
        # Initially all should be available
        all_locks = lock.list_all_locks()
        available_count = sum(1 for l in all_locks if l.status == LockStatus.AVAILABLE)
        assert available_count >= 4  # At least the 4 standard environment types
        
        # Acquire some locks
        lock.acquire_dev(timeout=2, purpose="List test dev")
        lock.acquire_test(timeout=2, purpose="List test test")
        
        # Check updated status
        all_locks = lock.list_all_locks()
        locked_envs = [l.environment for l in all_locks if l.status == LockStatus.LOCKED]
        assert "dev" in locked_envs
        assert "test" in locked_envs
        
        lock.release_all()
    
    def test_generic_acquire(self, tmp_path):
        """Test generic acquire method."""
    pass
        lock = EnvironmentLock(lock_dir=tmp_path)
        
        # Test generic acquire
        success = lock.acquire("custom_env", timeout=2, purpose="Custom environment")
        assert success
        
        # Check status
        status = lock.check_lock_status("custom_env")
        assert status.status == LockStatus.LOCKED
        assert status.metadata.environment == "custom_env"
        
        # Release
        success = lock.release("custom_env")
        assert success
        
        # Should be available now
        status = lock.check_lock_status("custom_env")
        assert status.status == LockStatus.AVAILABLE


def test_concurrent_access_simulation(tmp_path):
    """Test concurrent access from multiple threads."""
    results = []
    errors = []
    lock_dir = tmp_path
    
    def worker(worker_id):
        """Worker thread function."""
    pass
        try:
            lock = EnvironmentLock(lock_dir=lock_dir)
            success = lock.acquire_dev(timeout=1, purpose=f"Worker {worker_id}")
            results.append((worker_id, success))
            if success:
                time.sleep(0.1)  # Hold lock briefly
                lock.release_all()
        except Exception as e:
            errors.append((worker_id, str(e)))
    
    # Start multiple threads trying to acquire the same lock
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i))
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # Only one thread should have succeeded in acquiring
    successful = [r for r in results if r[1] is True]
    assert len(successful) == 1
    
    # Others should have failed with timeout
    failed_with_timeout = len([e for e in errors if "timeout" in e[1].lower() or "could not acquire" in e[1].lower()])
    assert failed_with_timeout == 4


if __name__ == "__main__":
    # Run tests manually if executed directly
    import sys
    import tempfile
    from pathlib import Path
    
    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from environment_lock import (
        EnvironmentLock, 
        EnvironmentType, 
        LockStatus,
        LockAcquisitionTimeout,
        LockNotHeldError
    )
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        test_instance = TestEnvironmentLock()
        
        print("Running basic lock acquisition test...")
        test_instance.test_basic_lock_acquisition(tmp_path)
        print("✓ Passed")
        
        print("Running context manager test...")
        test_instance.test_context_manager(tmp_path)
        print("✓ Passed")
        
        print("Running concurrent access test...")
        test_concurrent_access_simulation(tmp_path)
        print("✓ Passed")
        
        print("
All manual tests passed!")