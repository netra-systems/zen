#!/usr/bin/env python3
"""Test script to verify encoding fixes display correctly"""

print("\n=== Testing ASCII Box Drawing Characters ===\n")

# Test the separators used in agent_cli.py
print("=" * 75)
print("🤖 Netra Agent CLI - Interactive Mode")
print("=" * 75)
print()

# Test the box borders used in error messages
print("+==============================================================================+")
print("|                         ❌ PAYLOAD SIZE EXCEEDED                              |")
print("+==============================================================================+")
print()

print("+==============================================================================+")
print("|                      ⚠️  LARGE PAYLOAD WARNING                                |")
print("+==============================================================================+")
print()

# Show what the old characters would have looked like
print("=== Original Unicode characters (may display incorrectly) ===")
print("━" * 75)
print("╔══════════════════════════════════════════════════════════════════════════════╗")
print("║ Box with Unicode characters                                                   ║")
print("╚══════════════════════════════════════════════════════════════════════════════╝")
print()

print("✅ ASCII replacements should display correctly on all terminals!")