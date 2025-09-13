"""
File System Helpers for Agent Isolation Testing

Common utilities for file system isolation testing.
"""

import asyncio
import logging
import os
import random
import shutil
import tempfile
from typing import Any, Dict

logger = logging.getLogger(__name__)

async def simulate_file_operations(tenant_id: str, file_path: str, duration: float) -> Dict[str, Any]:
    """Simulate file I/O operations for a tenant."""
    start_time = time.time()
    operations_count = 0
    bytes_written = 0
    bytes_read = 0
    
    end_time = start_time + duration
    test_data = b"test data " * 100  # 900 bytes per write
    
    try:
        while time.time() < end_time:
            # Write operation
            with open(file_path, "ab") as f:
                f.write(test_data)
                bytes_written += len(test_data)
                operations_count += 1
            
            # Read operation  
            if operations_count % 5 == 0:  # Read every 5th operation
                try:
                    with open(file_path, "rb") as f:
                        data = f.read()
                        bytes_read += len(data)
                        operations_count += 1
                except Exception:
                    pass  # File might be being written to
            
            # Brief pause between operations
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"File operation error for tenant {tenant_id}: {e}")
    
    actual_duration = time.time() - start_time
    io_rate = operations_count / actual_duration if actual_duration > 0 else 0
    
    return {
        "tenant_id": tenant_id,
        "operations_count": operations_count,
        "bytes_written": bytes_written,
        "bytes_read": bytes_read,
        "duration": actual_duration,
        "io_rate": io_rate
    }

async def simulate_disk_usage(tenant_id: str, temp_dir: str, max_mb: int) -> Dict[str, Any]:
    """Simulate disk space usage for a tenant."""
    start_time = time.time()
    files_created = 0
    space_used_bytes = 0
    
    try:
        # Create files until we reach the limit
        file_size_kb = 100  # 100KB per file
        file_size_bytes = file_size_kb * 1024
        max_bytes = max_mb * 1024 * 1024
        
        while space_used_bytes < max_bytes:
            file_path = os.path.join(temp_dir, f"file_{files_created}.dat")
            
            # Create file with random data
            test_data = os.urandom(file_size_bytes)
            
            with open(file_path, "wb") as f:
                f.write(test_data)
            
            space_used_bytes += file_size_bytes
            files_created += 1
            
            # Brief pause to allow other operations
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"Disk usage simulation error for tenant {tenant_id}: {e}")
    
    duration = time.time() - start_time
    space_used_mb = space_used_bytes / (1024 * 1024)
    
    return {
        "tenant_id": tenant_id,
        "files_created": files_created,
        "space_used_mb": space_used_mb,
        "duration": duration,
        "creation_rate": files_created / duration if duration > 0 else 0
    }

async def concurrent_file_access(tenant_id: str, base_dir: str, file_pattern: str, duration: float) -> Dict[str, Any]:
    """Simulate concurrent file access for a tenant."""
    start_time = time.time()
    operations_count = 0
    corruption_errors = 0
    
    # Create tenant-specific files
    file_paths = []
    for i in range(5):  # 5 files per tenant
        file_path = os.path.join(base_dir, f"tenant_{tenant_id}_file_{i}.dat")
        file_paths.append(file_path)
        
        # Initialize file with known data
        try:
            with open(file_path, "wb") as f:
                initial_data = f"{tenant_id}_initial_data_{i}".encode() * 100
                f.write(initial_data)
        except Exception as e:
            logger.error(f"Failed to initialize file {file_path}: {e}")
    
    end_time = start_time + duration
    
    try:
        while time.time() < end_time:
            # Randomly select a file to operate on
            file_path = random.choice(file_paths)
            
            # Randomly choose operation type
            operation = random.choice(["read", "write", "append"])
            
            try:
                if operation == "read":
                    with open(file_path, "rb") as f:
                        data = f.read()
                        # Verify data integrity
                        if data and tenant_id.encode() not in data:
                            corruption_errors += 1
                
                elif operation == "write":
                    with open(file_path, "wb") as f:
                        new_data = f"{tenant_id}_write_{operations_count}".encode() * 50
                        f.write(new_data)
                
                elif operation == "append":
                    with open(file_path, "ab") as f:
                        append_data = f"{tenant_id}_append_{operations_count}".encode()
                        f.write(append_data)
                
                operations_count += 1
                
            except Exception as e:
                logger.warning(f"File operation error for {tenant_id}: {e}")
            
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"Concurrent access error for tenant {tenant_id}: {e}")
    
    # Cleanup tenant files
    for file_path in file_paths:
        try:
            os.unlink(file_path)
        except Exception:
            pass
    
    duration = time.time() - start_time
    access_rate = operations_count / duration if duration > 0 else 0
    
    return {
        "tenant_id": tenant_id,
        "operations_count": operations_count,
        "corruption_errors": corruption_errors,
        "duration": duration,
        "access_rate": access_rate
    }

import time  # Add missing import
