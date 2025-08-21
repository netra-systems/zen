#!/usr/bin/env python3
"""Validation helper functions for corpus creation."""

from typing import Any, Dict, List

VALID_TYPES = ["failed_request", "tool_use", "simple_chat", "rag_pipeline"]
REQUIRED = ["prompt", "response", "workload_type"]

def check_fields(entry, errors):
    """Check required fields."""
    for f in REQUIRED:
        if f not in entry or not entry[f]:
            errors.append(f"Missing or empty field '{f}'")

def check_type(entry, errors):
    """Check workload type."""
    if entry.get("workload_type") not in VALID_TYPES:
        errors.append(f"Invalid workload_type '{entry.get('workload_type')}'")

async def validate_handler(entry, run_id, handler):
    """Validate with handler."""
    errors = []
    check_fields(entry, errors)
    check_type(entry, errors)
    if errors:
        return await handle_errors(errors, handler, run_id)
    return {'success': True, 'entry': entry}

async def handle_errors(errors, handler, run_id):
    """Handle errors."""
    try:
        return await call_handler(errors, handler, run_id)
    except Exception:
        return {'success': False, 'errors': errors}

async def call_handler(errors, handler, run_id):
    """Call validation handler."""
    return await handler.handle_document_validation_error(
        filename="corpus_entry",
        validation_errors=errors,
        run_id=run_id,
        original_error=ValueError("Validation failed")
    )

def get_validator():
    """Get validator."""
    return SimpleVal()

class SimpleVal:
    """Simple validator."""
    def validate_entry(self, e):
        """Validate entry."""
        errs = []
        check_fields(e, errs)
        check_type(e, errs)
        return len(errs) == 0, errs

async def validate_simple(entry, validator):
    """Validate simple."""
    ok, errs = validator.validate_entry(entry)
    if not ok:
        return {'success': False, 'errors': errs}
    return {'success': True, 'entry': entry}

async def validate_all(data, run_id, handler, validator):
    """Validate all entries."""
    valid = []
    for i, e in enumerate(data):
        print(f"\nValidating entry {i + 1}...")
        r = await validate_one(e, run_id, handler, validator)
        process_result(r, e, valid, i)
    return valid

async def validate_one(entry, run_id, handler, validator):
    """Validate one entry."""
    if handler:
        return await validate_handler(entry, run_id, handler)
    else:
        return await validate_simple(entry, validator)

def process_result(r, entry, valid, i):
    """Process result."""
    if r['success']:
        add_valid(entry, valid, i)
    elif r.get('method') == 'relaxed_validation':
        add_warning(entry, valid, i)
    else:
        show_fail(r, i)

def add_valid(entry, valid, i):
    """Add valid entry."""
    valid.append(entry)
    print(f"✅ Entry {i + 1} is valid")

def add_warning(entry, valid, i):
    """Add with warning."""
    valid.append(entry)
    print(f"⚠️  Entry {i + 1} accepted with warnings")

def show_fail(r, i):
    """Show failure."""
    print(f"❌ Entry {i + 1} validation failed")
    print_errors(r)

def print_errors(r):
    """Print errors."""
    if 'errors' in r:
        for e in r['errors']:
            print(f"   - {e}")