"""
Gunicorn configuration for Auth Service
Optimized for GCP Cloud Run with proper worker management
"""
import os
import multiprocessing
import signal
import sys

# Import IsolatedEnvironment for consistent environment access
try:
    from auth_service.auth_core.isolated_environment import get_env
except ImportError:
    # Fallback for when imports may not be available during gunicorn setup
    def get_env():
        class FallbackEnv:
            def get(self, key, default=None):
                return os.getenv(key, default)
        return FallbackEnv()

# Server socket
bind = f"0.0.0.0:{get_env().get('PORT', '8080')}"
backlog = 2048

# Worker processes
# Cloud Run recommends 1-2 workers for CPU-optimized instances
workers = int(get_env().get('GUNICORN_WORKERS', '2'))
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 50  # Randomize worker restarts to avoid all workers restarting at once
timeout = 120  # Worker timeout
graceful_timeout = 30  # Time to wait for workers to finish serving requests during restart
keepalive = 5  # Seconds to wait for requests on Keep-Alive connections

# Threading
threads = int(get_env().get('GUNICORN_THREADS', '4'))
thread_type = 'gthread'

# Process naming
proc_name = 'netra-auth-service'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = get_env().get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Stats
statsd_host = get_env().get('STATSD_HOST', None)
if statsd_host:
    statsd_prefix = 'netra.auth.gunicorn'

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