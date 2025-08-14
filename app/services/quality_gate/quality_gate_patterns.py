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