"""
Gunicorn configuration for Auth Service
Uses SSOT AuthEnvironment for all configuration access.
"""
import os
import multiprocessing
import signal
import sys

# Use SSOT AuthEnvironment for all configuration
try:
    from auth_service.auth_core.auth_environment import get_auth_env
    auth_env = get_auth_env()
    environment = auth_env.get_environment()
except ImportError:
    # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
    # Fallback for when AuthEnvironment is not available during bootstrap
    from shared.isolated_environment import get_env
    env_manager = get_env()
    environment = env_manager.get('ENVIRONMENT', 'development').lower()
    if environment not in ['production', 'staging', 'development', 'test']:
        environment = 'development'

# Server socket with environment-specific defaults using SSOT
try:
    port = str(auth_env.get_auth_service_port())
    host = auth_env.get_auth_service_host()
except (NameError, AttributeError):
    # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
    # Fallback when AuthEnvironment not available
    from shared.isolated_environment import get_env
    env_manager = get_env()
    port = env_manager.get('PORT', '8080')
    host = "0.0.0.0"

bind = f"{host}:{port}"
backlog = 2048

# Worker processes with environment-specific defaults
try:
    # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
    from shared.isolated_environment import get_env
    env_manager = get_env()
    worker_count = env_manager.get('GUNICORN_WORKERS')
    if not worker_count:
        if environment == 'production':
            workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Production scaling
        elif environment == 'staging':
            workers = 2  # Moderate workers for staging
        elif environment == 'development':
            workers = 1  # Single worker for development
        elif environment == 'test':
            workers = 1  # Single worker for test isolation
        else:
            workers = 2  # Safe default
    else:
        workers = int(worker_count)
except Exception:
    workers = 2  # Safe fallback

worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 50  # Randomize worker restarts to avoid all workers restarting at once
timeout = 120  # Worker timeout
graceful_timeout = 30  # Time to wait for workers to finish serving requests during restart
keepalive = 5  # Seconds to wait for requests on Keep-Alive connections

# Threading with environment-specific defaults
try:
    # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
    from shared.isolated_environment import get_env
    env_manager = get_env()
    thread_count = env_manager.get('GUNICORN_THREADS')
    if not thread_count:
        if environment == 'production':
            threads = 4  # Standard threading for production
        elif environment == 'staging':
            threads = 4  # Production-like for staging
        elif environment == 'development':
            threads = 2  # Fewer threads for development
        elif environment == 'test':
            threads = 1  # Minimal threading for tests
        else:
            threads = 4  # Safe default
    else:
        threads = int(thread_count)
except Exception:
    threads = 4  # Safe fallback

thread_type = 'gthread'

# Process naming
proc_name = 'netra-auth-service'

# Logging with environment-specific defaults using SSOT
accesslog = '-'
errorlog = '-'

try:
    loglevel = auth_env.get_log_level().lower()
except (NameError, AttributeError):
    # SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
    # Fallback when AuthEnvironment not available
    from shared.isolated_environment import get_env
    env_manager = get_env()
    log_level = env_manager.get('LOG_LEVEL')
    if not log_level:
        if environment == 'production':
            loglevel = 'warning'  # Less verbose in production
        elif environment == 'staging':
            loglevel = 'info'     # Standard info level for staging
        elif environment == 'development':
            loglevel = 'debug'    # Verbose debugging in development
        elif environment == 'test':
            loglevel = 'error'    # Minimal logging in tests
        else:
            loglevel = 'info'     # Safe default
    else:
        loglevel = log_level.lower()

access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# SSOT FIX: Use IsolatedEnvironment instead of direct os.environ access
# Stats - only configure if explicitly set
from shared.isolated_environment import get_env
env_manager = get_env()
statsd_host = env_manager.get('STATSD_HOST')
if statsd_host:
    statsd_prefix = 'netra.auth.gunicorn'
else:
    # No default statsd configuration - only use when explicitly configured
    pass

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed for local development)
keyfile = None
certfile = None


def worker_int(worker):
    """Handle worker interrupt signal"""
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker):
    """Called just before a worker is forked"""
    server.log.info(f"Pre-fork worker with pid: {worker.pid}")


def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info(f"Worker spawned with pid: {worker.pid}")


def worker_abort(worker):
    """Called just after a worker exited on SIGABRT signal"""
    worker.log.error(f"Worker {worker.pid} aborted!")


def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forking new master process")


def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Server is ready. Spawning workers")


def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Starting Gunicorn server")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP"""
    server.log.info("Reloading workers")


def on_exit(server):
    """Called just before exiting"""
    server.log.info("Shutting down Gunicorn server")


def child_exit(server, worker):
    """Called just after a worker has been exited, in the master process"""
    # Prevent ProcessLookupError by not trying to kill already-dead workers
    server.log.info(f"Worker {worker.pid} exited")


def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed"""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")


# Signal handling for graceful shutdown
def handle_term(*args):
    """Handle SIGTERM for graceful shutdown"""
    sys.exit(0)


def handle_int(*args):
    """Handle SIGINT for graceful shutdown"""
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_term)
signal.signal(signal.SIGINT, handle_int)

# Preload application for better memory usage
preload_app = True

# Enable reuse of port (helps with container restarts)
reuse_port = True
