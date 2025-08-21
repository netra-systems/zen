"""Quality Gate Service Pattern Definitions"""


class QualityPatterns:
    """Pattern definitions for quality validation"""
    
    # Generic phrases that indicate low-quality content
    GENERIC_PHRASES = [
        r"it is important to note that",
        r"generally speaking",
        r"in general",
        r"as we know",
        r"it should be noted",
        r"one could argue",
        r"it goes without saying",
        r"needless to say",
        r"at the end of the day",
        r"when all is said and done",
        r"for all intents and purposes",
        r"in today's world",
        r"in this day and age",
        r"since the dawn of time",
        r"throughout history",
        r"in conclusion",
        r"to summarize",
        r"all things considered",
        r"it is worth mentioning"
    ]
    
    # Vague optimization terms without specifics
    # These patterns detect vague language that lacks specificity
    # We want to catch phrases like "optimize things" but NOT "optimize GPU utilization"
    VAGUE_TERMS = [
        r"just\s+optimize",
        r"optimize\s+(things|stuff|it|everything|something)",
        r"improve\s+(things|stuff|it|everything|something)",
        r"enhance\s+(things|stuff|it|everything|something)",
        r"make\s+(?:it\s+)?better",
        r"more\s+efficient(?!\s+(by|than))",
        r"consider\s+optimizing",
        r"think about\s+improving",
        r"look into\s+enhancing",
        r"you might want to",
        r"you could try",
        r"perhaps you should"
    ]
    
    # Circular reasoning patterns
    CIRCULAR_PATTERNS = [
        r"to improve.*you should improve",
        r"optimize.*by optimizing",
        r"better.*through better",
        r"enhance.*by enhancing",
        r"for better.*use better",
        r"improve.*to improve",
        r"increase.*by increasing",
        r"reduce.*by reducing",
        r"fix.*by fixing"
    ]
    
    # Domain-specific terms for Netra (indicates good content)
    DOMAIN_TERMS = [
        "latency", "throughput", "batch size", "token", "inference",
        "quantization", "pruning", "distillation", "cache", "memory",
        "GPU", "CPU", "TPU", "FLOPS", "bandwidth", "utilization",
        "p50", "p95", "p99", "QPS", "RPS", "ms", "microseconds",
        "cost per token", "cost per request", "TCO", "ROI",
        "model size", "parameter count", "attention heads", "layers",
        "beam search", "temperature", "top-p", "top-k", "context window",
        "KV cache", "flash attention", "tensor parallel", "pipeline parallel"
    ]
    
    # Error message specific patterns (indicates high specificity for errors)
    ERROR_SPECIFIC_PATTERNS = {
        'error_codes': r'\b[A-Z_]+_[A-Z0-9_]+\b|\b[A-Z]{3,}_\d+\b',
        'timestamps': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?',
        'service_identifiers': r'\b\w+-\w+-v?\d+\.\d+\.\d+\b|\b\w+://[\w\-.:/@]+\b',
        'database_connections': r'\b(max_connections|connection_timeout|pool_size)\s*[=:]\s*\d+',
        'system_commands': r'(SELECT|UPDATE|ALTER|systemctl|pg_dump|pip install)\s+[\w\s\-=.()>*]+',
        'log_levels': r'\b(ERROR|WARN|INFO|DEBUG|FATAL|TRACE):\s',
        'stack_trace_indicators': r'(at\s+[\w.]+\([^)]+\)|Traceback|Exception in|Stack trace)',
        'process_ids': r'\bpid[:\s=]*\d+\b|\bprocess\s+\d+\b',
        'port_numbers': r':\d{2,5}(?:/|\b)',
        'memory_addresses': r'0x[0-9a-fA-F]+',
        'file_paths': r'/[\w\-./]+\.\w+|[A-Z]:\\[\w\\\-.]+\.\w+',
        'configuration_keys': r'\b\w+_\w+\s*[=:]\s*(?:true|false|\d+|"[^"]*")'
    }
    
    # Error message domain terms
    ERROR_DOMAIN_TERMS = [
        "timeout", "connection", "database", "query", "transaction",
        "deadlock", "rollback", "constraint", "index", "table",
        "exception", "error", "failure", "crash", "abort",
        "memory leak", "segfault", "null pointer", "buffer overflow",
        "authentication", "authorization", "permission", "access denied",
        "network", "socket", "TCP", "UDP", "HTTP", "SSL", "TLS",
        "thread", "process", "lock", "mutex", "semaphore",
        "heap", "stack", "garbage collection", "out of memory"
    ]