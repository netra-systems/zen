#!/usr/bin/env python3
"""I/O helper functions for corpus creation."""

import json
from typing import List, Optional

def print_header():
    """Print header."""
    print("=" * 60)
    print("CORPUS DATA COLLECTION")
    print("=" * 60)

def print_instructions():
    """Print instructions."""
    print("\nPlease provide your corpus data in JSON format.")
    print("The format should be a JSON array of objects, each containing:")
    print_fields()

def print_fields():
    """Print field descriptions."""
    print("  - prompt: The user's question or request")
    print("  - response: The system's answer")
    print("  - workload_type: One of [failed_request, tool_use, simple_chat, rag_pipeline]")

def print_example():
    """Print example."""
    print("\nExample:")
    show_ex()
    print("\n" + "=" * 60)
    print("Paste your JSON data below (press Enter twice when done):")
    print("-" * 60)

def show_ex():
    """Show example JSON."""
    ex = [{"prompt": "What is Netra's pricing?",
           "response": "Netra offers flexible pricing plans...",
           "workload_type": "simple_chat"}]
    print(json.dumps(ex, indent=2))

def collect_input():
    """Collect input."""
    lines = []
    loop_input(lines)
    return "\n".join(lines).strip()

def loop_input(lines):
    """Loop for input."""
    empty = 0
    while True:
        result = get_line(lines, empty)
        if result is False:
            break
        empty = result

def get_line(lines, empty):
    """Get one line."""
    try:
        line = input()
        return handle_line(line, lines, empty)
    except EOFError:
        return False

def handle_line(line, lines, empty):
    """Handle input line."""
    if line == "":
        return check_empty(empty)
    return add_line(line, lines)

def check_empty(empty):
    """Check empty lines."""
    new_count = empty + 1
    if new_count >= 2:
        return False
    return new_count

def add_line(line, lines):
    """Add non-empty line."""
    lines.append(line)
    return 0

def parse_json(text):
    """Parse JSON."""
    if not text:
        print("❌ No input provided")
        return None
    return try_parse(text)

def try_parse(text):
    """Try to parse JSON."""
    try:
        data = json.loads(text)
        return validate_array(data)
    except json.JSONDecodeError as e:
        print_err(e)
        return None

def validate_array(data):
    """Validate JSON array."""
    if not isinstance(data, list):
        print("❌ Error: Input must be a JSON array")
        return None
    return data

def print_err(e):
    """Print parse error."""
    print(f"❌ Invalid JSON format: {e}")
    print("\nPlease ensure your input is valid JSON.")

def print_summary(corpus):
    """Print summary."""
    print("\n" + "=" * 60)
    print("CORPUS SUMMARY")
    print("=" * 60)
    print(f"Total valid entries: {len(corpus)}")
    print_counts(corpus)
    print_preview(corpus)

def print_counts(corpus):
    """Print counts."""
    counts = get_counts(corpus)
    print("\nEntries by workload type:")
    for wt, c in sorted(counts.items()):
        print(f"  - {wt}: {c}")

def get_counts(corpus):
    """Get workload counts."""
    counts = {}
    for e in corpus:
        wt = e["workload_type"]
        counts[wt] = counts.get(wt, 0) + 1
    return counts

def print_preview(corpus):
    """Print preview."""
    if not corpus:
        return
    print("\nFirst entry preview:")
    show_first(corpus[0])

def show_first(f):
    """Show first entry."""
    print_text("  Prompt", f['prompt'], 50)
    print_text("  Response", f['response'], 50)
    print(f"  Type: {f['workload_type']}")

def print_text(label, text, max_len):
    """Print text."""
    if len(text) > max_len:
        print(f"{label}: {text[:max_len]}...")
    else:
        print(f"{label}: {text}")

def print_results(r, corpus):
    """Print results."""
    print("\n🎉 Corpus creation complete!")
    print(f"  ✓ File: {r.get('filename', 'corpus-content.json')}")
    print(f"  ✓ Entries: {r.get('entries', len(corpus))}")
    print(f"  ✓ Size: {r.get('file_size', 0):,} bytes")
    msg = "\nYou can now run 'python corpus_to_xml.py' "
    print(msg + "to generate categorized XML files.")

def print_failure(r):
    """Print failure."""
    print("\n⚠️  Failed to save corpus.")
    if 'message' in r:
        print(f"  Reason: {r['message']}")