#!/usr/bin/env python3
"""Value-based corpus validation using existing corpus_admin validators."""

import os
import sys


from typing import Any, Dict, List

from netra_backend.app.agents.corpus_admin.corpus_creation_validation import (
    REQUIRED,
    check_fields,
    print_errors,
    validate_simple,
)
from netra_backend.app.agents.corpus_admin.corpus_creation_validation import SimpleVal as BaseValidator


class ValueCorpusValidator(BaseValidator):
    """Extended validator for value-based corpus with flexible metadata."""
    
    def validate_entry(self, entry):
        """Validate entry with relaxed workload_type rules."""
        errors = []
        check_fields(entry, errors)
        
        # Allow any string for workload_type (no restriction)
        if "workload_type" in entry:
            if not isinstance(entry["workload_type"], str):
                errors.append("workload_type must be a string")
        
        # Validate optional metadata
        if "metadata" in entry:
            self.validate_metadata(entry["metadata"], errors)
        
        # Validate optional domain
        if "domain" in entry:
            if not isinstance(entry["domain"], str):
                errors.append("domain must be a string")
        
        return len(errors) == 0, errors
    
    def validate_metadata(self, metadata, errors):
        """Validate metadata structure."""
        if not isinstance(metadata, dict):
            errors.append("metadata must be a dictionary")
            return
        
        for key, value in metadata.items():
            if not isinstance(key, str):
                errors.append(f"Metadata key '{key}' must be string")
            if value is None:
                errors.append(f"Metadata value for '{key}' is None")

def get_value_validator():
    """Get value corpus validator."""
    return ValueCorpusValidator()

async def validate_value_corpus(entries, handler=None, run_id=None):
    """Validate all value corpus entries."""
    validator = get_value_validator()
    valid_entries = []
    
    for i, entry in enumerate(entries):
        print(f"Validating entry {i + 1}...")
        result = await validate_simple(entry, validator)
        
        if result['success']:
            valid_entries.append(entry)
            print(f"✅ Entry {i + 1} valid")
        else:
            print(f"❌ Entry {i + 1} failed")
            print_errors(result)
    
    return valid_entries

def validate_sync(entries):
    """Synchronous validation for simple use cases."""
    validator = get_value_validator()
    valid_entries = []
    errors_found = []
    
    for i, entry in enumerate(entries):
        is_valid, errors = validator.validate_entry(entry)
        if is_valid:
            valid_entries.append(entry)
        else:
            errors_found.extend([f"Entry {i+1}: {e}" for e in errors])
    
    return valid_entries, errors_found