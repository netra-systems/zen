"""
Log filter patterns for different startup modes.

Contains pattern definitions used by LogFilter for noise reduction.
"""

# Comprehensive noise patterns for aggressive filtering
NOISE_PATTERNS = [
    # Webpack/Build noise
    r"webpack\.Progress",
    r"[U+25CB] Compiling",
    r"Compiled.*in \d+ms",
    r"Ready in \d+ms",
    r"HMR.*updated",
    r"Fast Refresh",
    
    # NPM warnings
    r"npm WARN",
    r"npm notice",
    r"deprecated.*package",
    r"DeprecationWarning",
    
    # File watching
    r"Watching for file changes",
    r"File changed:",
    r"Recompiling\.\.\.",
    
    # Health checks
    r"Health check passed",
    r"Heartbeat.*ok",
    r"Status: healthy",
    
    # Session/middleware setup
    r"Session middleware config:",
    r"Security headers middleware initialized",
    r"CORS middleware configured",
    
    # Database connection noise
    r"Context impl PostgresqlImpl",
    r"Will assume transactional DDL",
    r"REAL connection (established|closed)",
    r"connection (open|closed)",
    r"\[ClickHouse\] Connecting to instance",
    r"\[ClickHouse\] REAL connection",
    r"PostgreSQL async engine created",
    r"Current revision:",
    r"Database is up to date",
    
    # Service initialization
    r"UnifiedToolRegistry initialized",
    r"Response Generator initialized",
    r"Quality Gate Service initialized",
    r"Quality Monitoring Service initialized",
    r"Multiprocessing configured",
    r"Registered telemetry for service",
    r"SyntheticDataService initialized",
    r"Registered agent:",
    r"Performance.*initialized",
    r"Performance.*started",
    r"Background task.*added",
    r"Task Task-\d+ added",
    
    # HTTP request noise
    r"HTTP Request:",
    r"Request: (GET|POST|OPTIONS|HEAD)",
    r"WebSocket.*accepted",
    r"Invalid HTTP request received",
    
    # Startup process noise
    r"Application startup\.\.\.",
    r"Waiting for application startup",
    r"Started server process",
    r"Using dev user:",
    r"Application startup complete",
    r"Uvicorn running on",
    r"pytest detected in sys.modules",
    r"Checking database migrations",
    r"Loading key manager",
    r"Key manager loaded",
    r"Initializing ClickHouse tables",
    r"ClickHouse tables initialization complete",
    r"Starting database optimization",
    r"Database optimization completed",
    r"Database index optimization scheduled",
    r"Comprehensive monitoring started",
    r"Database connection monitoring",
    
    # Environment/validation
    r"Database environment validation",
    r"Environment variables loaded",
    r"Configuration validation passed",
    r"Schema validation.*successfully",
    r"Extra tables in database",
    
    # Development environment specific
    r"Created development configuration",
    r"Loading DATABASE_URL",
    r"Populated.*config for development",
    r"Populated.*secrets for development",
]

# Patterns to condense in standard mode
STANDARD_CONDENSE_PATTERNS = [
    (r"Creating ClickHouse table.*: (\w+)", "Table: {1}"),
    (r"Successfully ensured table exists: (\w+)", "[U+2713] {1}"),
    (r"Registered agent: (\w+)", "Agent: {1}"),
    (r"Task Task-\d+ added to background manager", "Background task added"),
]

# Critical patterns to always show
CRITICAL_PATTERNS = [
    r"ERROR",
    r"CRITICAL",
    r"Failed",
    r"error while attempting to bind",
    r"Missing.*credential",
    r"not found",
    r"Connection refused",
    r"timeout",
]

# Key startup messages for minimal mode
KEY_STARTUP_MESSAGES = [
    "started on port", "system ready", "all services ready",
    "backend ready", "frontend ready", "auth service started",
    "server started", "listening on", "ready for connections"
]

# Critical startup failures for silent mode
CRITICAL_STARTUP_FAILURES = [
    "failed to start", "startup failed", "cannot bind",
    "port already in use", "connection refused"
]

# Common noise patterns for standard mode filtering
COMMON_NOISE_PATTERNS = [
    r"webpack\.Progress", r"npm WARN", r"Watching for file changes",
    r"Health check passed", r"Compiling", r"HTTP Request:",
    r"connection (open|closed)", r"WebSocket.*accepted"
]