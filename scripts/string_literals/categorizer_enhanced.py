#!/usr/bin/env python3
"""
Enhanced String Literal Categorizer
Context-aware categorization with hierarchical categories and confidence scoring.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    from .scanner_core import RawLiteral
except ImportError:
    # Handle direct execution
    from scanner_core import RawLiteral


@dataclass
class CategorizedLiteral:
    """Enhanced categorized literal with confidence and context."""
    value: str
    file: str
    line: int
    category: str
    subcategory: Optional[str] = None
    confidence: float = 1.0
    context: str = ''
    type_hint: str = 'unknown'
    
    @property
    def full_category(self) -> str:
        """Get full hierarchical category."""
        if self.subcategory:
            return f"{self.category}.{self.subcategory}"
        return self.category


class EnhancedStringLiteralCategorizer:
    """Context-aware categorizer with hierarchical categories and confidence scoring."""
    
    def __init__(self):
        """Initialize categorizer with enhanced patterns."""
        self._setup_patterns()
        self._setup_context_hints()
        self._setup_file_path_hints()
        
    def _setup_patterns(self) -> None:
        """Setup comprehensive categorization patterns with confidence scores."""
        self.patterns = {
            'configuration': {
                'env_var': [
                    (r'^[A-Z][A-Z_]+[A-Z]$', 0.7),  # ALL_CAPS environment variables (lower confidence)
                    (r'^(NETRA|APP|DB|REDIS|LOG|ENV)_', 0.95),  # Known prefixes
                ],
                'config_key': [
                    (r'_(url|uri|host|port|key|token|secret|password)$', 0.9),
                    (r'^(max|min|default|timeout|retry|limit)_', 0.85),
                    (r'_config$', 0.8),
                    (r'^(redis|postgres|clickhouse|jwt)_', 0.85),
                ],
                'setting': [
                    (r'^(enable|disable|allow|deny)_', 0.8),
                    (r'_(enabled|disabled|allowed|denied)$', 0.8),
                    (r'^(debug|verbose|quiet|strict)$', 0.7),
                ],
                'connection': [
                    (r'connection_string|connect_', 0.9),
                    (r'_pool|_connection|_client', 0.8),
                ]
            },
            
            'paths': {
                'api': [
                    (r'^/api/v\d+', 0.95),  # Versioned API endpoints
                    (r'^/api/', 0.9),
                    (r'^/(auth|users|threads|messages|agents)', 0.85),
                ],
                'websocket': [
                    (r'^/ws|^/websocket', 0.95),
                    (r'websocket_', 0.8),
                ],
                'file': [
                    (r'\.(py|json|xml|yaml|yml|env|log|txt|md)$', 0.9),
                    (r'^\./', 0.8),  # Relative paths
                ],
                'directory': [
                    (r'^(app|frontend|scripts|tests|SPEC|docs)/', 0.9),
                    (r'^[a-z_]+/$', 0.7),  # Directory endings
                ],
                'url': [
                    (r'^https?://', 0.95),
                    (r'^ftp://', 0.95),
                ]
            },
            
            'identifiers': {
                'component': [
                    (r'_(agent|manager|executor|service|handler|processor)$', 0.9),
                    (r'^(auth|main|frontend)_service$', 0.95),
                ],
                'field': [
                    (r'_id$', 0.85),
                    (r'_(name|type|status|state)$', 0.8),
                    (r'^(user|thread|message|agent)_', 0.8),
                ],
                'class': [
                    (r'^[A-Z][a-zA-Z]*[A-Z][a-zA-Z]*$', 0.7),  # CamelCase
                ],
                'function': [
                    (r'^[a-z_]+$', 0.6),  # snake_case functions
                ]
            },
            
            'database': {
                'table': [
                    (r'^(threads|messages|users|agents|configs|sessions)$', 0.95),
                    (r'^[a-z_]+s$', 0.7),  # Plural table names
                ],
                'column': [
                    (r'_(at|by|id|name|type|status|created|updated|deleted)$', 0.9),
                    (r'^(id|name|email|password|token)$', 0.85),
                ],
                'sql': [
                    (r'^(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|ON)$', 0.95),
                    (r'^(ORDER BY|GROUP BY|HAVING|LIMIT|OFFSET)$', 0.95),
                ],
                'query': [
                    (r'SELECT .+ FROM', 0.9),
                    (r'INSERT INTO', 0.9),
                    (r'UPDATE .+ SET', 0.9),
                ]
            },
            
            'events': {
                'handler': [
                    (r'^(on|emit|handle)_', 0.9),
                    (r'_(handler|listener)$', 0.85),
                ],
                'type': [
                    (r'_(created|updated|deleted|connected|disconnected|started|stopped)$', 0.95),
                    (r'^websocket_', 0.85),
                    (r'^(thread|message|user|agent)_', 0.8),
                ],
                'lifecycle': [
                    (r'^(before|after)_', 0.8),
                    (r'_(init|cleanup|shutdown)$', 0.8),
                ]
            },
            
            'metrics': {
                'measurement': [
                    (r'_(count|total|rate|duration|latency|size|bytes)$', 0.9),
                    (r'^(request|response|error|success)_', 0.85),
                ],
                'status': [
                    (r'^(error|success|failure|timeout)_', 0.9),
                    (r'_(errors|successes|failures|timeouts)$', 0.9),
                ],
                'performance': [
                    (r'_(seconds|milliseconds|microseconds)$', 0.95),
                    (r'_(cpu|memory|disk|network)_', 0.9),
                ]
            },
            
            'states': {
                'status': [
                    (r'^(pending|active|completed|failed|error|success|running)$', 0.95),
                    (r'^(healthy|degraded|offline|online|ready)$', 0.95),
                ],
                'boolean': [
                    (r'^(enabled|disabled|true|false|yes|no)$', 0.95),
                ],
                'lifecycle': [
                    (r'^(created|updated|deleted|archived)$', 0.9),
                    (r'^(started|stopped|paused|resumed)$', 0.9),
                ]
            },
            
            'messages': {
                'log': [
                    (r'^(DEBUG|INFO|WARN|ERROR|FATAL):', 0.9),
                    (r'Starting|Stopping|Connecting|Connected|Disconnected', 0.8),
                ],
                'user': [
                    (r'^[A-Z][a-z].{20,}$', 0.6),  # User-facing messages
                ],
                'error': [
                    (r'^(Error|Failed|Exception|Invalid)', 0.85),
                    (r'not found|already exists|permission denied', 0.8),
                ],
                'success': [
                    (r'^(Success|Completed|Created|Updated|Deleted)', 0.8),
                ]
            },
            
            'documentation': {
                'docstring': [
                    (r'^\s*[A-Z][a-z].{30,}\.$', 0.7),  # Sentence-like docstrings
                ],
                'comment': [
                    (r'^#\s', 0.9),  # Comments
                    (r'^TODO|FIXME|NOTE|WARNING', 0.9),
                ],
                'markdown': [
                    (r'^#{1,6}\s', 0.9),  # Markdown headers
                    (r'^\*\*|^__', 0.8),  # Bold markdown
                ]
            },
            
            'formats': {
                'template': [
                    (r'\{[^}]+\}', 0.8),  # Template strings
                    (r'%[sd]|%\([^)]+\)', 0.8),  # Python format strings
                ],
                'regex': [
                    (r'\^|\$|\[|\]|\(|\)|\*|\+|\?|\\', 0.7),  # Regex patterns
                ],
                'json': [
                    (r'^\{.*\}$', 0.8),  # JSON-like strings
                    (r'^\[.*\]$', 0.8),  # JSON arrays
                ],
                'datetime': [
                    (r'\d{4}-\d{2}-\d{2}', 0.9),  # ISO dates
                    (r'%Y|%m|%d|%H|%M|%S', 0.9),  # datetime format codes
                ]
            }
        }
    
    def _setup_context_hints(self) -> None:
        """Setup context-based categorization hints."""
        self.context_hints = {
            'configuration': ['config', 'settings', 'env', 'environment'],
            'paths.api': ['route', 'endpoint', 'api', 'router'],
            'events': ['event', 'handler', 'listener', 'emit', 'on_'],
            'database': ['query', 'sql', 'table', 'column', 'db_'],
            'metrics': ['metric', 'measure', 'monitor', 'track'],
            'messages.log': ['log', 'logger', 'logging'],
            'messages.error': ['error', 'exception', 'fail'],
            'states': ['status', 'state', 'condition'],
            'documentation': ['doc', 'comment', 'description'],
            'formats.template': ['template', 'format', 'render']
        }
    
    def _setup_file_path_hints(self) -> None:
        """Setup file path based categorization hints."""
        self.file_path_hints = {
            'configuration': ['/config/', '/settings/', '.env', 'config.py'],
            'paths.api': ['/api/', '/routes/', '/endpoints/', 'router.py'],
            'database': ['/db/', '/database/', '/models/', '/schema/', 'migrations/'],
            'events': ['/events/', '/handlers/', '/listeners/'],
            'messages.log': ['/logs/', '/logging/', 'logger.py'],
            'messages.error': ['/errors/', '/exceptions/', 'error.py'],
            'documentation': ['/docs/', '.md', 'README', 'SPEC/'],
            'tests': ['/tests/', '/test/', '_test.py', 'test_'],
        }
    
    def _get_file_context_hints(self, file_path: str) -> List[str]:
        """Extract context hints from file path."""
        hints = []
        file_lower = file_path.lower()
        
        for category, patterns in self.file_path_hints.items():
            for pattern in patterns:
                if pattern in file_lower:
                    hints.append(category)
                    break
        
        return hints
    
    def _get_import_context(self, literal: RawLiteral) -> List[str]:
        """Analyze import context to provide categorization hints."""
        # This would ideally analyze the imports in the file
        # For now, we'll use basic heuristics based on context
        context = literal.context.lower()
        hints = []
        
        if 'config' in context or 'setting' in context:
            hints.append('configuration')
        if 'route' in context or 'api' in context:
            hints.append('paths.api')
        if 'event' in context or 'handler' in context:
            hints.append('events')
        if 'db' in context or 'query' in context:
            hints.append('database')
        if 'log' in context:
            hints.append('messages.log')
        if 'test' in context:
            hints.append('tests')
            
        return hints
    
    def _calculate_pattern_confidence(self, literal: str, pattern: str, base_confidence: float) -> float:
        """Calculate confidence score for a pattern match."""
        # Adjust confidence based on literal characteristics
        confidence = base_confidence
        
        # Higher confidence for exact matches
        if re.fullmatch(pattern, literal, re.IGNORECASE):
            confidence = min(1.0, confidence + 0.1)
        
        # Lower confidence for very short or very long strings
        if len(literal) < 3:
            confidence *= 0.7
        elif len(literal) > 100:
            confidence *= 0.8
            
        # Lower confidence for strings with spaces (likely messages)
        if ' ' in literal and len(literal.split()) > 2:
            confidence *= 0.6
            
        return confidence
    
    def _should_skip_literal(self, literal: str) -> bool:
        """Determine if a literal should be skipped entirely."""
        # Skip empty or very short strings
        if len(literal.strip()) < 2:
            return True
            
        # Skip very long strings (likely documentation)
        if len(literal) > 500:
            return True
            
        # Skip strings that are mostly whitespace
        if len(literal.strip()) < len(literal) * 0.3:
            return True
            
        # Skip common Python artifacts
        if literal in ['__main__', '__name__', '__doc__', '__all__']:
            return True
            
        return False
    
    def _apply_pattern_matching(self, literal: str) -> List[Tuple[str, str, float]]:
        """Apply pattern matching to categorize literal."""
        matches = []
        
        for category, subcategories in self.patterns.items():
            for subcategory, patterns in subcategories.items():
                for pattern, base_confidence in patterns:
                    if re.search(pattern, literal, re.IGNORECASE):
                        confidence = self._calculate_pattern_confidence(
                            literal, pattern, base_confidence
                        )
                        matches.append((category, subcategory, confidence))
                        
        return matches
    
    def _apply_context_hints(self, literal: RawLiteral) -> List[Tuple[str, str, float]]:
        """Apply context-based categorization."""
        hints = []
        
        # File path hints
        file_hints = self._get_file_context_hints(literal.file)
        for hint in file_hints:
            if '.' in hint:
                category, subcategory = hint.split('.', 1)
            else:
                category, subcategory = hint, 'general'
            hints.append((category, subcategory, 0.6))
        
        # Import/context hints
        import_hints = self._get_import_context(literal)
        for hint in import_hints:
            if '.' in hint:
                category, subcategory = hint.split('.', 1)
            else:
                category, subcategory = hint, 'general'
            hints.append((category, subcategory, 0.5))
        
        # Function/class context hints
        context_lower = literal.context.lower()
        for category_hint, keywords in self.context_hints.items():
            for keyword in keywords:
                if keyword in context_lower:
                    if '.' in category_hint:
                        category, subcategory = category_hint.split('.', 1)
                    else:
                        category, subcategory = category_hint, 'general'
                    hints.append((category, subcategory, 0.4))
                    break
        
        return hints
    
    def _smart_fallback_categorization(self, literal: str, raw_literal: RawLiteral) -> Tuple[str, str, float]:
        """Smart fallback when pattern matching fails."""
        value = literal.strip()
        
        # Check for common patterns that might be missed
        
        # Technical strings (version numbers, hashes, etc.)
        if re.match(r'^\d+\.\d+\.\d+', value):  # Version numbers
            return ('metadata', 'version', 0.7)
        
        if re.match(r'^[a-f0-9]{8,}$', value):  # Hex strings (hashes, IDs)
            return ('identifiers', 'hash', 0.7)
            
        # File extensions or MIME types
        if re.match(r'^[a-z]+/[a-z]+$', value):  # MIME types
            return ('formats', 'mime_type', 0.8)
            
        # Network related
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', value):  # IP addresses
            return ('network', 'ip_address', 0.9)
            
        if re.match(r':\d{1,5}$', value):  # Port numbers
            return ('network', 'port', 0.8)
        
        # Constants or enum-like values
        if value.isupper() and '_' in value:
            return ('constants', 'enum', 0.6)
            
        # Command line arguments
        if value.startswith('-') and len(value) > 1:
            return ('cli', 'argument', 0.8)
        
        # File paths that weren't caught
        if '/' in value or '\\' in value:
            return ('paths', 'file', 0.6)
            
        # Query parameters or form fields
        if '=' in value and len(value.split('=')) == 2:
            return ('web', 'parameter', 0.7)
            
        # Language constructs
        if value in ['self', 'cls', 'args', 'kwargs', 'None', 'True', 'False']:
            return ('language', 'keyword', 0.9)
            
        # Simple text content
        if ' ' in value and len(value.split()) >= 2:
            if value[0].isupper():  # Starts with capital
                return ('messages', 'user', 0.5)
            else:
                return ('content', 'text', 0.4)
        
        # Single words
        if value.isalpha() and len(value) > 2:
            return ('identifiers', 'name', 0.3)
            
        # Numeric strings
        if value.isdigit():
            return ('constants', 'number', 0.5)
            
        # Default fallback
        return ('uncategorized', 'unknown', 0.1)
    
    def categorize(self, raw_literal: RawLiteral) -> CategorizedLiteral:
        """Categorize a raw literal with enhanced context awareness."""
        literal = raw_literal.value
        
        # Skip if should be ignored
        if self._should_skip_literal(literal):
            return CategorizedLiteral(
                value=literal,
                file=raw_literal.file,
                line=raw_literal.line,
                category='ignored',
                subcategory='skipped',
                confidence=1.0,
                context=raw_literal.context,
                type_hint='skipped'
            )
        
        # Collect all potential categorizations
        all_matches = []
        
        # Pattern-based matching
        pattern_matches = self._apply_pattern_matching(literal)
        all_matches.extend(pattern_matches)
        
        # Context-based hints
        context_matches = self._apply_context_hints(raw_literal)
        all_matches.extend(context_matches)
        
        # Choose best match
        if all_matches:
            # Sort by confidence (highest first)
            all_matches.sort(key=lambda x: x[2], reverse=True)
            best_category, best_subcategory, best_confidence = all_matches[0]
        else:
            # Use smart fallback
            best_category, best_subcategory, best_confidence = self._smart_fallback_categorization(
                literal, raw_literal
            )
        
        # Determine type hint from subcategory
        type_hint = best_subcategory if best_subcategory != 'general' else best_category
        
        return CategorizedLiteral(
            value=literal,
            file=raw_literal.file,
            line=raw_literal.line,
            category=best_category,
            subcategory=best_subcategory,
            confidence=best_confidence,
            context=raw_literal.context,
            type_hint=type_hint
        )
    
    def categorize_batch(self, raw_literals: List[RawLiteral]) -> List[CategorizedLiteral]:
        """Categorize a batch of raw literals."""
        return [self.categorize(literal) for literal in raw_literals]
    
    def get_categorization_stats(self, categorized_literals: List[CategorizedLiteral]) -> Dict:
        """Get statistics about categorization results."""
        stats = {
            'total': len(categorized_literals),
            'by_category': {},
            'by_confidence': {'high': 0, 'medium': 0, 'low': 0},
            'uncategorized': 0,
            'avg_confidence': 0.0
        }
        
        total_confidence = 0.0
        
        for literal in categorized_literals:
            # Category stats
            full_cat = literal.full_category
            if full_cat not in stats['by_category']:
                stats['by_category'][full_cat] = 0
            stats['by_category'][full_cat] += 1
            
            # Confidence stats
            if literal.confidence >= 0.8:
                stats['by_confidence']['high'] += 1
            elif literal.confidence >= 0.5:
                stats['by_confidence']['medium'] += 1
            else:
                stats['by_confidence']['low'] += 1
                
            # Uncategorized count
            if literal.category == 'uncategorized':
                stats['uncategorized'] += 1
                
            total_confidence += literal.confidence
        
        if categorized_literals:
            stats['avg_confidence'] = total_confidence / len(categorized_literals)
            
        return stats


def categorize_literals(raw_literals: List[RawLiteral]) -> List[CategorizedLiteral]:
    """Convenience function to categorize a list of raw literals."""
    categorizer = EnhancedStringLiteralCategorizer()
    return categorizer.categorize_batch(raw_literals)


def print_categorization_report(categorized_literals: List[CategorizedLiteral]) -> None:
    """Print a comprehensive categorization report."""
    categorizer = EnhancedStringLiteralCategorizer()
    stats = categorizer.get_categorization_stats(categorized_literals)
    
    print(f"\n=== Enhanced Categorization Report ===")
    print(f"Total literals processed: {stats['total']}")
    print(f"Average confidence: {stats['avg_confidence']:.3f}")
    print(f"Uncategorized: {stats['uncategorized']} ({stats['uncategorized']/stats['total']*100:.1f}%)")
    
    print(f"\nConfidence Distribution:")
    print(f"  High (>=0.8): {stats['by_confidence']['high']} ({stats['by_confidence']['high']/stats['total']*100:.1f}%)")
    print(f"  Medium (0.5-0.8): {stats['by_confidence']['medium']} ({stats['by_confidence']['medium']/stats['total']*100:.1f}%)")
    print(f"  Low (<0.5): {stats['by_confidence']['low']} ({stats['by_confidence']['low']/stats['total']*100:.1f}%)")
    
    print(f"\nTop Categories:")
    sorted_categories = sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)
    for category, count in sorted_categories[:10]:
        percentage = count / stats['total'] * 100
        print(f"  {category}: {count} ({percentage:.1f}%)")
    
    if len(sorted_categories) > 10:
        print(f"  ... and {len(sorted_categories) - 10} more categories")


if __name__ == '__main__':
    # Example usage and testing
    from pathlib import Path
    import sys
    
    # Add the scripts directory to path to import scanner_core
    sys.path.insert(0, str(Path(__file__).parent))
    from scanner_core import RawLiteral
    
    # Test with some sample literals
    test_literals = [
        RawLiteral("NETRA_API_KEY", "config.py", 10, None, "load_config"),
        RawLiteral("/api/v1/threads", "routes.py", 25, None, "create_route"),
        RawLiteral("thread_created", "events.py", 15, None, "emit_event"),
        RawLiteral("SELECT * FROM users", "db.py", 30, None, "query_users"),
        RawLiteral("This is a user message", "ui.py", 40, None, "display_message"),
        RawLiteral("2024-01-15T10:30:00Z", "timestamp.py", 5, None, "format_date"),
        RawLiteral("error_count_total", "metrics.py", 20, None, "track_errors"),
    ]
    
    categorizer = EnhancedStringLiteralCategorizer()
    results = categorizer.categorize_batch(test_literals)
    
    print("=== Test Results ===")
    for result in results:
        print(f"'{result.value}' -> {result.full_category} (confidence: {result.confidence:.2f})")
    
    print_categorization_report(results)