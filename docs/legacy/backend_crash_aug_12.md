## Detailed Analysis of Backend Crash Issue

### The Problem

  The backend server starts successfully but crashes immediately after initialization with a semaphore leak warning. This happens consistently regardless of how the server is launched.

### Error Manifestation

  /opt/homebrew/Cellar/python@3.11/3.11.6_1/Frameworks/Python.framework/Versions/3.11/lib/python3.11/multiprocessing/resource_tracker.py:254: UserWarning: resource_tracker: There appear to be 8 leaked semaphore objects to clean up at 
  shutdown warnings.warn('resource_tracker: There appear to be %d '

### Root Cause Analysis

  1. What are Semaphores?

  - Semaphores are synchronization primitives used in multiprocessing
  - They control access to shared resources between processes
  - Python tracks these to ensure proper cleanup

  2. Why the Leak Occurs

  The leak happens because:
  - 8 semaphore objects are created during application startup
  - These semaphores are not properly released/closed
  - Python's resource tracker detects them as "leaked" at shutdown
  - The leak causes the process to terminate abnormally

  3. Where It's Happening

  Based on the startup sequence, the leak occurs after:
  ✓ Application startup completed
  ✓ Database validation passed
  ✓ Migrations checked (skipped in dev)
  ✓ Key manager loaded
  ✓ LLM manager initialized (disabled in dev)
  ✓ ClickHouse initialized (disabled in dev)
  ✓ Redis checked (disabled in dev)
  ✓ Startup checks completed
  ✗ CRASH - Semaphore leak detected

 ### Likely Culprits

  1. ThreadPoolExecutor in async_utils.py

  # Line 470 in app/core/async_utils.py
  run_in_threadpool._executor = ThreadPoolExecutor(max_workers=10)
  - Creates a thread pool with 10 workers
  - May be creating semaphores for thread synchronization
  - Not properly shut down during application lifecycle

  2. Multiprocessing During Import

  Some module imported during startup might be:
  - Creating a ProcessPool or multiprocessing.Manager
  - Using multiprocessing.Queue or Pipe
  - Not cleaning up these resources

  3. Third-party Library Issue

  Libraries that might create background processes:
  - uvicorn with multiple workers (though we're using single worker)
  - langchain or related AI libraries
  - clickhouse-driver or database connectors
  - Background task managers

  ### Why It Crashes the Backend

  1. Resource Exhaustion Protection: Python detects leaked semaphores as a potential resource leak
  2. Abnormal Termination: The warning triggers an exit to prevent resource exhaustion
  3. Cascading Failure: The sudden exit doesn't allow proper cleanup of other resources

  ### Evidence from Testing

  1. Consistent Behavior: Crashes after exact same sequence every time
  2. Always 8 Semaphores: The number is consistent, suggesting a fixed pool/queue size
  3. Happens Even with Services Disabled: Still occurs with Redis/ClickHouse/LLMs disabled
  4. Architecture Independent: Persists after fixing Python architecture issues

  ### The Impact

  - Backend becomes unusable - Crashes immediately after startup
  - Frontend can't connect - No backend API available
  - Development blocked - Can't run the full application stack

 ### Potential Solutions

  1. Find and fix the resource leak:
    - Identify which module creates the semaphores
    - Ensure proper cleanup with context managers or shutdown hooks
  2. Suppress the warning (temporary workaround):
    - Filter the warning but doesn't fix underlying issue
    - Risk of actual resource exhaustion over time
  3. Use different multiprocessing start method:
    - Try 'fork' instead of 'spawn' on macOS
    - May have other side effects
  4. Disable problematic components:
    - Systematically disable imports to isolate the issue
    - Replace ThreadPoolExecutor with alternative implementations

 ### Next Steps for Resolution

  To properly fix this, we would need to:
  1. Add logging to track when semaphores are created
  2. Use Python's faulthandler to get a proper stack trace
  3. Systematically disable components to isolate the problematic module
  4. Implement proper cleanup in the application lifecycle

  The issue is particularly challenging because it occurs during the import/initialization phase, making it hard to debug with normal application logging.