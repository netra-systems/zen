# Five Whys Root Cause Analysis - Docker & Test Issues
Date: 2025-09-03

## Issue 1: Initial Path Error Looking for Docker-Compose Files in Wrong Location

### Five Whys Analysis:

**1. Why did the initial path error occur?**
   - The UnifiedDockerManager's `_get_compose_file()` method (line 1109-1153) searches for compose files in a specific order, starting with the current directory.

**2. Why did it search in the current directory first?**
   - The code logic (line 1127-1131) checks Path(file_path).exists() for each compose file in the current directory before checking project root or parent directories.

**3. Why would the current directory be wrong?**
   - Tests or scripts might be executed from subdirectories (like `/tests/` or `/scripts/`) rather than the project root, causing the relative path resolution to fail.

**4. Why aren't tests always run from the project root?**
   - Different test runners, IDE configurations, or manual executions can change the working directory, and there's no enforcement of running from project root.

**5. Why doesn't the code handle this gracefully?**
   - While the code does have fallback logic to check parent directories (lines 1145-1151) and NETRA_PROJECT_ROOT environment variable (lines 1134-1142), it relies on relative path traversal which can fail in deeply nested execution contexts.

### Root Cause:
The path resolution logic assumes execution from or near the project root and doesn't have robust absolute path resolution for all execution contexts.

### Solution:
- Always use absolute paths based on the script location or git root
- Set NETRA_PROJECT_ROOT environment variable consistently
- Add validation at the start of test runs to ensure correct working directory

---

## Issue 2: ClickHouse Container Failed Health Check

### Five Whys Analysis:

**1. Why did the ClickHouse container fail its health check?**
   - The health check uses `wget -q -O- http://localhost:8123/ping` (line 89 in alpine-test.yml) which expects ClickHouse HTTP service to be ready.

**2. Why wasn't the ClickHouse HTTP service ready?**
   - ClickHouse can take 30-60 seconds to fully initialize, especially on first run when it needs to create databases and users.

**3. Why does it take so long to initialize?**
   - ClickHouse performs several initialization steps:
     - Creating default database (CLICKHOUSE_DB: test_analytics)
     - Setting up user accounts (CLICKHOUSE_USER: test)
     - Enabling access management (CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT: 1)
     - Starting both HTTP (8123) and TCP (9000) listeners

**4. Why doesn't the health check account for this delay?**
   - The health check has:
     - start_period: 60s (should be sufficient)
     - retries: 20 with 10s intervals (200s total)
     - But the wget command might fail immediately if the port isn't even listening yet

**5. Why does wget fail immediately instead of waiting?**
   - The wget health check fails fast if the port isn't open, and Docker might not properly honor the start_period in all scenarios, especially under resource constraints.

### Root Cause:
The health check method (wget) fails immediately when the service port isn't available, and ClickHouse initialization can be slow under resource constraints or when volumes need initialization.

### Solution:
- Use a more robust health check: `clickhouse-client --query "SELECT 1"` instead of wget
- Increase start_period to 90s for slower systems
- Add resource limits to prevent memory exhaustion during startup
- Consider using tmpfs for test data to speed up initialization

---

## Issue 3: Test Cleanup Was Successful But Tests Couldn't Run

### Five Whys Analysis:

**1. Why couldn't tests run after successful cleanup?**
   - The cleanup removed containers and volumes, but the subsequent startup might have failed or been incomplete.

**2. Why would startup fail after successful cleanup?**
   - Possible reasons:
     - Port conflicts with other processes
     - Docker daemon resource exhaustion
     - Network cleanup issues leaving orphaned networks
     - Volume driver issues after forced removal

**3. Why would there be port conflicts or resource issues?**
   - Multiple test runs in parallel or incomplete cleanup from previous runs could leave:
     - Zombie processes holding ports
     - Docker networks in inconsistent state
     - Memory/disk constraints from accumulated test artifacts

**4. Why doesn't the system detect and resolve these issues?**
   - The UnifiedDockerManager has port conflict detection but might not catch all scenarios:
     - System processes outside Docker using the same ports
     - Race conditions in port allocation
     - Docker daemon state inconsistencies

**5. Why do Docker daemon state inconsistencies occur?**
   - Forced container removals, interrupted operations, or resource exhaustion can leave Docker's internal state corrupted, requiring daemon restart.

### Root Cause:
Docker daemon state corruption or resource exhaustion from repeated test runs without proper cleanup between runs.

### Solution:
- Implement pre-test validation of Docker daemon health
- Add Docker system prune before test runs to clean up orphaned resources
- Use dynamic port allocation to avoid conflicts
- Add retry logic with exponential backoff for container startup
- Monitor and limit Docker resource usage

---

## Comprehensive Solution Strategy

### Immediate Actions:
1. **Fix Path Resolution:**
   ```python
   # Add to UnifiedDockerManager._get_compose_file()
   import git
   repo = git.Repo(search_parent_directories=True)
   project_root = repo.working_dir
   ```

2. **Improve ClickHouse Health Check:**
   ```yaml
   healthcheck:
     test: ["CMD", "clickhouse-client", "--query", "SELECT 1"]
     interval: 15s
     timeout: 10s
     retries: 30
     start_period: 90s
   ```

3. **Add Pre-Test Cleanup:**
   ```python
   # Add to test setup
   subprocess.run(["docker", "system", "prune", "-f", "--volumes"])
   subprocess.run(["docker", "network", "prune", "-f"])
   ```

### Long-term Improvements:
1. **Implement Circuit Breaker Pattern** for Docker operations
2. **Add Telemetry** to track Docker operation success rates
3. **Create Dedicated Test Environments** with isolated networks
4. **Implement Health Check Orchestration** that validates all services before proceeding
5. **Add Automatic Recovery** mechanisms for common failure scenarios

### Monitoring & Prevention:
1. **Log Docker daemon metrics** (CPU, memory, disk I/O)
2. **Track test execution patterns** to identify resource bottlenecks
3. **Implement gradual rollout** of configuration changes
4. **Create alerts** for repeated health check failures
5. **Document troubleshooting runbooks** for common scenarios