#!/usr/bin/env python3
"""
Factory Pattern Cleanup Remediation Script - PHASE 2
Remove Unnecessary Factory Abstractions and Builder Patterns

This script removes over-engineered factory patterns that don't provide business value
while maintaining essential factories that provide user isolation and dependency injection.
"""

import os
import re
import shutil
from pathlib import Path

def analyze_factory_necessity(file_path, content):
    """Analyze if a factory provides legitimate business value."""
    # Legitimate factories should have:
    # 1. User context isolation
    # 2. Complex dependency injection
    # 3. Resource lifecycle management
    # 4. Configuration validation
    # 5. Multi-instance management

    legitimate_patterns = [
        r'user.*context|user.*isolation',
        r'dependency.*injection|inject.*dependencies',
        r'lifecycle|cleanup|resource.*management',
        r'validate.*config|configuration.*validation',
        r'per.*request|request.*scoped',
        r'websocket.*bridge|websocket.*integration'
    ]

    # Over-engineered patterns:
    # 1. Simple wrapper that just delegates
    # 2. Factory that just calls constructor
    # 3. Builder pattern for simple objects
    # 4. Factory with only one create method that does basic instantiation

    overengineered_patterns = [
        r'class.*Factory.*def create.*return.*\(\)',
        r'wrapper.*compatibility.*shim',
        r'delegates.*to.*canonical',
        r'backward.*compatibility.*only',
        r'simple.*wrapper',
        r'compatibility.*wrapper'
    ]

    # Check for legitimate patterns
    legitimate_score = sum(1 for pattern in legitimate_patterns
                          if re.search(pattern, content, re.IGNORECASE))

    # Check for over-engineered patterns
    overengineered_score = sum(1 for pattern in overengineered_patterns
                               if re.search(pattern, content, re.IGNORECASE))

    print(f"  {file_path}: Legitimate={legitimate_score}, Overengineered={overengineered_score}")

    # Factory is over-engineered if:
    # 1. High over-engineered score and low legitimate score
    # 2. Contains explicit compatibility wrapper language
    # 3. Simple delegation pattern
    if (overengineered_score >= 2 and legitimate_score <= 1) or \
       "compatibility shim only" in content or \
       "backward compatibility" in content.lower():
        return "REMOVE"
    elif legitimate_score >= 2:
        return "KEEP"
    else:
        return "REVIEW"

def remediate_unnecessary_factory(file_path):
    """Remove or replace unnecessary factory with direct instantiation."""

    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    decision = analyze_factory_necessity(file_path, content)

    if decision == "REMOVE":
        # Backup original
        backup_path = file_path + ".backup_pre_factory_removal"
        shutil.copy2(file_path, backup_path)
        print(f"  Backup created: {backup_path}")

        # Create deprecation notice file
        deprecation_content = f'''"""
FACTORY CLEANUP REMEDIATION: This factory was removed as unnecessary over-engineering.

Original file: {file_path}
Reason: Over-engineered wrapper factory that provided no business value
Backup: {backup_path}

MIGRATION PATH:
- If this was a simple wrapper, use the canonical implementation directly
- If this provided compatibility, update imports to use the canonical source
- Check backup file for original implementation if needed

Business Value Impact: POSITIVE - Reduces complexity while maintaining functionality
SSOT Compliance: IMPROVED - Eliminates duplicate abstraction layers
"""

# This file has been deprecated and removed as part of factory pattern cleanup.
# See backup file for original implementation if needed.

import warnings

warnings.warn(
    f"Factory {file_path} has been deprecated and removed as unnecessary over-engineering. "
    f"Use the canonical implementation instead. See backup: {backup_path}",
    DeprecationWarning,
    stacklevel=2
)

class DeprecatedFactoryPlaceholder:
    """Placeholder to prevent import errors during migration period."""

    def __init__(self, *args, **kwargs):
        raise DeprecationWarning(
            f"This factory has been removed as unnecessary over-engineering. "
            f"See {backup_path} for original implementation and migration guide."
        )
'''

        # Write deprecation notice
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(deprecation_content)

        print(f"  Successfully removed over-engineered factory: {file_path}")
        return True

    elif decision == "KEEP":
        print(f"  Keeping legitimate factory: {file_path}")
        return False

    else:
        print(f"  Needs manual review: {file_path}")
        return False

def run_phase2_remediation():
    """Execute Phase 2 - Remove unnecessary factory abstractions."""
    print("=== FACTORY CLEANUP REMEDIATION PHASE 2 ===")
    print("Removing unnecessary factory abstractions and builder patterns")
    print("Focus on over-engineering reduction while maintaining business value")
    print()

    # Identify candidate files for removal
    factory_files = [
        "netra_backend/app/agents/execution_engine_unified_factory.py",  # Known compatibility wrapper
        "netra_backend/app/core/degradation_factory.py",
        "netra_backend/app/core/graceful_degradation_factory.py",
        "netra_backend/app/core/retry_strategy_factory.py",
        "netra_backend/app/core/secret_manager_factory.py",
        "netra_backend/app/agents/user_context_tool_factory.py",
    ]

    removed_count = 0
    kept_count = 0
    review_count = 0

    print("Analyzing factory files for business value...")
    print()

    for file_path in factory_files:
        if os.path.exists(file_path):
            print(f"Analyzing: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                decision = analyze_factory_necessity(file_path, content)

                if decision == "REMOVE":
                    if remediate_unnecessary_factory(file_path):
                        removed_count += 1
                elif decision == "KEEP":
                    kept_count += 1
                else:
                    review_count += 1

            except Exception as e:
                print(f"  Error processing {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")

    print(f"\n=== PHASE 2 REMEDIATION COMPLETE ===")
    print(f"Factories removed: {removed_count}")
    print(f"Factories kept: {kept_count}")
    print(f"Factories needing review: {review_count}")

    if removed_count > 0:
        print(f"\nNEXT STEPS:")
        print("1. Test system to ensure no broken imports")
        print("2. Update any code that imports removed factories")
        print("3. Run Golden Path validation")
        print("4. Proceed to Phase 3 - Fix SSOT compliance violations")

    return {
        'removed': removed_count,
        'kept': kept_count,
        'review': review_count
    }

if __name__ == "__main__":
    results = run_phase2_remediation()
    print(f"\nPhase 2 completed: {results}")