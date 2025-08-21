"""
Validation and preprocessing operations for corpus management
"""

from typing import Dict, List
from netra_backend.app.logging_config import central_logger


class ValidationManager:
    """Handles validation and preprocessing of corpus records"""
    
    def __init__(self):
        self.validation_cache: Dict[str, bool] = {}
        
    def validate_records(self, records: List[Dict]) -> Dict:
        """
        Validate corpus records
        
        Args:
            records: List of corpus records to validate
            
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        for i, record in enumerate(records):
            # Check required fields
            if "prompt" not in record:
                errors.append(f"Record {i}: missing 'prompt' field")
            if "response" not in record:
                errors.append(f"Record {i}: missing 'response' field")
            if "workload_type" not in record:
                errors.append(f"Record {i}: missing 'workload_type' field")
            
            # Validate workload type
            valid_types = [
                "simple_chat", "rag_pipeline", "tool_use",
                "multi_turn_tool_use", "failed_request", "custom_domain"
            ]
            if record.get("workload_type") not in valid_types:
                errors.append(f"Record {i}: invalid workload_type '{record.get('workload_type')}'")
            
            # Check field lengths
            if len(record.get("prompt", "")) > 100000:
                errors.append(f"Record {i}: prompt exceeds maximum length")
            if len(record.get("response", "")) > 100000:
                errors.append(f"Record {i}: response exceeds maximum length")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def preprocess_record(self, record: Dict) -> Dict:
        """
        Preprocess a single record before insertion
        
        Args:
            record: Raw record data
            
        Returns:
            Preprocessed record
        """
        processed = record.copy()
        
        # Set defaults
        processed.setdefault("workload_type", "general")
        processed.setdefault("prompt", "")
        processed.setdefault("response", "")
        processed.setdefault("metadata", {})
        processed.setdefault("domain", "general")
        
        # Trim whitespace
        if isinstance(processed.get("prompt"), str):
            processed["prompt"] = processed["prompt"].strip()
        if isinstance(processed.get("response"), str):
            processed["response"] = processed["response"].strip()
        
        return processed
    
    def validate_corpus_data(self, corpus_data) -> Dict:
        """
        Validate corpus creation data
        
        Args:
            corpus_data: Corpus creation data
            
        Returns:
            Validation result
        """
        errors = []
        
        if not corpus_data.name or not corpus_data.name.strip():
            errors.append("Corpus name is required")
        
        if len(corpus_data.name) > 255:
            errors.append("Corpus name exceeds maximum length of 255 characters")
        
        if hasattr(corpus_data, 'description') and corpus_data.description:
            if len(corpus_data.description) > 1000:
                errors.append("Corpus description exceeds maximum length of 1000 characters")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def sanitize_table_name(self, corpus_id: str) -> str:
        """
        Generate a safe table name from corpus ID
        
        Args:
            corpus_id: Corpus identifier
            
        Returns:
            Sanitized table name
        """
        # Replace hyphens with underscores for ClickHouse compatibility
        safe_id = corpus_id.replace('-', '_')
        return f"netra_content_corpus_{safe_id}"
    
    def clear_validation_cache(self):
        """Clear the validation cache"""
        self.validation_cache.clear()
        central_logger.info("Validation cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """
        Get validation cache statistics
        
        Returns:
            Cache statistics
        """
        return {
            "cache_size": len(self.validation_cache),
            "cached_validations": list(self.validation_cache.keys())
        }