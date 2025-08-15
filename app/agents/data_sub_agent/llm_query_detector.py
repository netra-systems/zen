"""Detect and fix LLM-generated ClickHouse queries.

LLMs may generate queries with incorrect syntax, especially for ClickHouse
Nested structures. This module detects such queries and fixes them.
"""

import re
from typing import Tuple, List, Dict, Any
from app.logging_config import central_logger as logger


class LLMQueryDetector:
    """Detects and fixes queries that appear to be LLM-generated."""
    
    # Patterns that suggest a query was LLM-generated
    LLM_INDICATORS = [
        # LLMs often use SQL-style array access instead of ClickHouse functions
        r'metrics\.\w+\[\w+\]',  # metrics.value[idx] instead of arrayElement
        
        # LLMs might generate simplified queries without proper subqueries
        r'SELECT\s+arrayFirstIndex.*if\s*\(\s*idx',  # Direct SELECT with if(idx...)
        
        # LLMs often miss ClickHouse-specific syntax
        r'SELECT\s+\*.*metrics\.value\[',  # SELECT * with array access
        
        # LLMs might use standard SQL instead of ClickHouse syntax
        r'ARRAY\[.*\]',  # ARRAY[...] instead of [...]
        r'\.get\(',  # .get() method instead of arrayElement
        
        # Common LLM query patterns that are incorrect
        r'metrics\[.*\]\[.*\]',  # Double array access
    ]
    
    # Query patterns that are definitely NOT from our query builder
    NON_BUILDER_PATTERNS = [
        # Our builder always uses arrayElement for array access
        (r'metrics\.value\[', 'Uses bracket notation instead of arrayElement'),
        
        # Our builder uses specific query structure with subqueries
        (r'^SELECT\s+arrayFirstIndex.*if\(idx.*metrics\.', 
         'Direct SELECT without subquery structure'),
        
        # Our builder doesn't generate lowercased function names
        (r'arrayfirstindex|arrayelement', 'Lowercased ClickHouse functions'),
    ]
    
    @classmethod
    def is_likely_llm_generated(cls, query: str) -> Tuple[bool, List[str]]:
        """Check if a query appears to be LLM-generated.
        
        Args:
            query: The query to check
            
        Returns:
            Tuple of (is_llm_generated, list of reasons)
        """
        reasons = []
        
        # Check for LLM indicators
        for pattern in cls.LLM_INDICATORS:
            if re.search(pattern, query, re.IGNORECASE):
                reasons.append(f"Contains pattern: {pattern}")
        
        # Check for non-builder patterns
        for pattern, description in cls.NON_BUILDER_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                reasons.append(description)
        
        # Additional heuristics
        if cls._has_suspicious_structure(query):
            reasons.append("Query structure doesn't match our templates")
        
        is_llm = len(reasons) > 0
        
        if is_llm:
            logger.warning(f"Detected likely LLM-generated query: {reasons}")
            logger.debug(f"Query: {query[:200]}...")
        
        return is_llm, reasons
    
    @classmethod
    def _has_suspicious_structure(cls, query: str) -> bool:
        """Check for suspicious query structure."""
        query_lower = query.lower()
        
        # Check for correlation queries without proper structure
        if ('arrayfirstindex' in query_lower and 
            'if(idx' in query_lower.replace(' ', '') and
            'from (' not in query_lower):  # Missing subquery
            return True
        
        # Check for mixed case issues (LLMs might inconsistently case)
        if 'SELECT' in query and 'select' in query:
            return True
        
        return False
    
    @classmethod
    def fix_llm_query(cls, query: str) -> str:
        """Fix a query that appears to be LLM-generated.
        
        Args:
            query: The LLM-generated query
            
        Returns:
            Fixed query with proper ClickHouse syntax
        """
        fixed = query
        
        # Fix array access syntax
        fixed = cls._fix_array_access(fixed)
        
        # Fix function casing
        fixed = cls._fix_function_names(fixed)
        
        # Fix correlation query structure if needed
        fixed = cls._fix_correlation_structure(fixed)
        
        # Remove any SQL-style syntax
        fixed = cls._fix_sql_style_syntax(fixed)
        
        if fixed != query:
            logger.info("Fixed LLM-generated query")
            logger.debug(f"Original: {query[:200]}...")
            logger.debug(f"Fixed: {fixed[:200]}...")
        
        return fixed
    
    @classmethod
    def _fix_array_access(cls, query: str) -> str:
        """Fix array access to use arrayElement."""
        # Match metrics.field[index] and replace with arrayElement
        pattern = r'(\w+)\.(\w+)\[([^\]]+)\]'
        
        def replace_func(match):
            table = match.group(1)
            field = match.group(2)
            index = match.group(3)
            
            # Only fix metrics table arrays
            if table == 'metrics':
                return f"arrayElement({table}.{field}, {index})"
            return match.group(0)
        
        return re.sub(pattern, replace_func, query)
    
    @classmethod
    def _fix_function_names(cls, query: str) -> str:
        """Fix ClickHouse function name casing."""
        # ClickHouse functions that might be miscased
        functions = {
            'arrayfirstindex': 'arrayFirstIndex',
            'arrayelement': 'arrayElement',
            'arrayexists': 'arrayExists',
            'arraylength': 'arrayLength',
            'todate': 'toDate',
            'tointervalday': 'toIntervalDay',
        }
        
        result = query
        for wrong, correct in functions.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            result = pattern.sub(correct, result)
        
        return result
    
    @classmethod
    def _fix_correlation_structure(cls, query: str) -> str:
        """Fix correlation query structure if it's missing subquery."""
        # Detect simplified correlation query
        if ('arrayFirstIndex' in query and 
            'if(idx' in query.replace(' ', '') and
            'FROM (' not in query):
            
            # This is a simplified correlation query that needs restructuring
            # For now, just ensure array syntax is correct
            # A full restructure would require parsing and rebuilding
            logger.warning("Detected simplified correlation query - applying basic fixes only")
        
        return query
    
    @classmethod
    def _fix_sql_style_syntax(cls, query: str) -> str:
        """Fix SQL-style syntax to ClickHouse syntax."""
        # Fix ARRAY[...] to [...]
        query = re.sub(r'ARRAY\s*\[([^\]]+)\]', r'[\1]', query, flags=re.IGNORECASE)
        
        # Fix other SQL-isms as needed
        
        return query
    
    @classmethod
    def validate_and_fix(cls, query: str) -> Tuple[str, Dict[str, Any]]:
        """Validate a query and fix if LLM-generated.
        
        Args:
            query: The query to validate
            
        Returns:
            Tuple of (fixed_query, metadata)
        """
        is_llm, reasons = cls.is_likely_llm_generated(query)
        
        metadata = {
            'is_llm_generated': is_llm,
            'detection_reasons': reasons,
            'was_fixed': False
        }
        
        if is_llm:
            fixed_query = cls.fix_llm_query(query)
            metadata['was_fixed'] = (fixed_query != query)
            
            logger.warning(
                f"LLM query detected and {'fixed' if metadata['was_fixed'] else 'validated'}"
            )
            
            return fixed_query, metadata
        
        return query, metadata