This audit finds the "Docker Test Environment Stability - Remediation Plan" to be comprehensive, well-structured, and correctly prioritized. It accurately identifies the root causes of the instability (resource exhaustion, orphaned resources, configuration divergence, and lack of cleanup mechanisms) and proposes appropriate solutions across immediate, short-term, and long-term horizons.

However, the audit has identified several critical areas where the implementation details require correction, risk mitigation, or improvement to ensure the plan's success and safety.

### Overall Assessment: Strong Plan, Implementation Refinements Needed

The strategy is sound, but the execution requires specific adjustments regarding safety, portability, and correctness.

### Detailed Audit Findings and Recommendations

#### 1\. Immediate Actions (P0)

**1.1. CRITICAL SAFETY RISK: Aggressive Volume Pruning**

  * **Section:** 1. Clean Orphaned Resources
  * **Observation:** The command `docker system prune -f --volumes` is highly aggressive. It removes *all* unused volumes on the Docker host, not just those related to this specific test environment.
  * **Risk:** High risk of unintended data loss for other projects or development setups on the same machine.
  * **Recommendation:** Modify the immediate cleanup to exclude volumes. The plan correctly addresses volume cleanup later within the test runner (`docker compose down --volumes`).

<!-- end list -->

```bash
# Revised Safer Immediate Cleanup:
# ... (Keep the targeted network and container removal commands) ...

# Prune system (containers, networks, images, build cache - NOT volumes)
docker system prune -f
```

**1.2. PostgreSQL Configuration Trade-offs**

  * **Section:** 2. Fix Test Environment Resource Usage
  * **Observation:** The plan changes PostgreSQL settings to `fsync=on` and `synchronous_commit=on`. This significantly increases data durability (matching production) but drastically increases disk I/O, which will slow down test execution.
  * **Recommendation:** Ensure this trade-off is acceptable. If the primary goal is maximizing test speed while maintaining stability (which the resource limits should address), consider keeping these settings optimized for performance.

<!-- end list -->

```yaml
# Suggested PostgreSQL command if speed is prioritized
  command: |
    postgres
      -c shared_buffers=128MB
      -c effective_cache_size=512MB
      # Consider keeping these off for faster tests:
      -c fsync=off
      -c synchronous_commit=off
```

#### 2\. Short-term Fixes (P1)

**2.1. Environment Lock Implementation Flaws (Portability, Usability, Correctness)**

  * **Section:** 2. Implement Environment Lock
  * **Observation:** The proposed `EnvironmentLock` implementation has several critical flaws:
    1.  **Portability:** It uses `fcntl`, which is unavailable on Windows.
    2.  **Correctness:** The `timeout` parameter is ignored because `LOCK_NB` (non-blocking) is used, causing an immediate failure if the lock is held.
    3.  **Usability:** It does not implement the context manager protocol (`__enter__`/`__exit__`), making it difficult to guarantee that locks are released.
  * **Recommendation:** Replace the implementation with a cross-platform library like `filelock` and implement it as a context manager.

<!-- end list -->

```python
# Recommended implementation using 'filelock' library
# Requires: pip install filelock
# File: test_framework/environment_lock.py

from pathlib import Path
from filelock import Timeout, FileLock
import logging

logger = logging.getLogger(__name__)

class EnvironmentLocker:
    """Manages environment locks (Cross-platform Context Manager)"""
    LOCK_DIR = Path.home() / ".netra" / "locks"

    def __init__(self, env_name, timeout=60):
        self.LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.LOCK_DIR / f"{env_name}.lock"
        self.lock = FileLock(self.lock_file)
        self.timeout = timeout
        self.env_name = env_name

    def __enter__(self):
        try:
            logger.info(f"Acquiring lock for {self.env_name}...")
            self.lock.acquire(timeout=self.timeout)
            return self
        except Timeout:
            raise RuntimeError(
                f"Failed to acquire environment lock for {self.env_name} "
                f"within {self.timeout}s."
            )

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()
        logger.info(f"Released lock for {self.env_name}.")

# Usage in unified_test_runner.py would change to:
# with EnvironmentLocker("test"):
#    ... run tests ...
```

**2.2. Resource Monitor Corrections and Safety**

  * **Section:** 3. Add Resource Monitor
  * **Issue 1 (Bug):** The code raises `ResourceError`, but this custom exception is not defined.
  * **Issue 2 (Safety):** The `cleanup_if_needed` logic removes the oldest containers if the total count exceeds `MAX_CONTAINERS`. This risks removing containers that are actively running if a previous suite failed to clean up.
  * **Issue 3 (Robustness):** Sorting containers by the string representation of `Created` time can be unreliable.
  * **Recommendation:** Define the exception, enhance the cleanup logic to prioritize stopped containers, and use datetime parsing for sorting.

<!-- end list -->

```python
# File: test_framework/resource_monitor.py
# Ensure these imports are present
from dateutil import parser as date_parser # Requires python-dateutil

# Define Custom Exception
class ResourceError(Exception):
    """Custom exception for resource related issues."""
    pass

class DockerResourceMonitor:
    # ... (rest of the class) ...
    def cleanup_if_needed(self):
        """Clean up if approaching limits"""
        containers = self.client.containers.list(all=True)
        test_containers = [c for c in containers if 'test-' in c.name]
        
        if len(test_containers) > self.MAX_CONTAINERS:
            logger.warning(f"Too many test containers: {len(test_containers)}")

            # Prioritize removing stopped containers
            stopped_containers = [c for c in test_containers if c.status in ('exited', 'created')]
            
            # Sort by parsed datetime object (oldest first)
            stopped_containers.sort(key=lambda c: date_parser.parse(c.attrs['Created']))

            # Calculate how many need to be removed
            excess_count = len(test_containers) - self.MAX_CONTAINERS
            containers_to_remove = stopped_containers[:excess_count]

            for container in containers_to_remove:
                logger.info(f"Removing old/stopped container: {container.name}")
                container.remove(force=True)
```

#### 3\. Long-term Solutions (P2)

**3.1. Automated Cleanup Cron - Missing Prerequisites and Deployment**

  * **Section:** 3. Automated Cleanup Cron
  * **Issue 1 (Missing Prerequisite):** The script relies on filtering resources using `--filter "label=netra.env=test"`. This label is missing from the provided Docker Compose configurations. The script will not function as intended.
  * **Issue 2 (Deployment Practice):** The script uses a Python infinite loop (`while True: time.sleep(1800)`). It is more reliable and efficient to use the operating system's scheduler (e.g., `cron`).
  * **Recommendation:**
    1.  Add labels to all services and volumes in `docker-compose.test.yml` (or the base configuration).
    2.  Remove the loop/sleep from the Python script and schedule it via `crontab`.

**Required YAML addition (docker-compose.test.yml):**

```yaml
services:
  test-postgres:
    # ... other configs ...
    labels:
      - "netra.env=test"
# ... (Apply to all other services) ...

volumes:
  test_postgres_data:
    labels:
      - "netra.env=test"
```

**Revised `scripts/docker_cleanup_cron.py` (Snippet):**

```python
# ... imports ...
def cleanup():
    """Periodic cleanup of Docker resources"""
    # ... (Cleanup logic remains the same) ...

if __name__ == "__main__":
    # Remove while loop and time.sleep
    cleanup()
```

**Crontab Implementation (Linux/macOS):**

```bash
# Add this line to the crontab (crontab -e) to run every 30 minutes
*/30 * * * * /path/to/venv/bin/python /path/to/scripts/docker_cleanup_cron.py >> /var/log/docker_cleanup.log 2>&1
```