#!/usr/bin/env python3
"""Interactive script to create corpus-content.json from user input."""

import sys
import asyncio
import uuid
from typing import List, Dict, Any

# Handle both direct execution and module imports
try:
    from .corpus_creation_helpers import get_handlers, HANDLERS_AVAILABLE
    from .corpus_creation_io import (
        print_header, print_instructions, print_example,
        collect_input, parse_json, print_summary,
        print_results, print_failure
    )
    from .corpus_creation_validation import (
        get_validator, validate_handler, validate_simple,
        validate_all
    )
    from .corpus_creation_storage import (
        save_file, index_corpus, handle_error, get_sample_data
    )
except ImportError:
    from corpus_creation_helpers import get_handlers, HANDLERS_AVAILABLE
    from corpus_creation_io import (
        print_header, print_instructions, print_example,
        collect_input, parse_json, print_summary,
        print_results, print_failure
    )
    from corpus_creation_validation import (
        get_validator, validate_handler, validate_simple,
        validate_all
    )
    from corpus_creation_storage import (
        save_file, index_corpus, handle_error, get_sample_data
    )

# Initialize handlers and validators
v_handler, i_handler, u_handler = get_handlers()
validator = get_validator() if not HANDLERS_AVAILABLE else None

# Print initialization status
if HANDLERS_AVAILABLE:
    print("✅ Running with advanced corpus handlers")
else:
    print("ℹ️  Running in standalone mode (basic validation only)")

async def validate_entry(entry, run_id):
    """Validate a single entry."""
    if v_handler:
        return await validate_handler(entry, run_id, v_handler)
    else:
        return await validate_simple(entry, validator)

async def index_entry(doc_id, entry, run_id):
    """Index a corpus entry."""
    if i_handler:
        try:
            from .corpus_creation_storage import index_entry as idx
        except ImportError:
            from corpus_creation_storage import index_entry as idx
        await idx(doc_id, entry, run_id, i_handler)
    else:
        print(f"  ✓ Would index: {doc_id} (standalone mode)")

async def get_user_corpus(run_id):
    """Get corpus from user."""
    print_header()
    print_instructions()
    print_example()
    return await process_input(run_id)

async def process_input(run_id):
    """Process user input."""
    text = collect_input()
    data = parse_json(text)
    if data is None:
        return []
    return await validate_all(data, run_id, v_handler, validator)

async def save_corpus(corpus, filename, run_id):
    """Save corpus to file."""
    try:
        return await do_save(corpus, filename, run_id)
    except Exception as e:
        return await handle_save_err(e, filename, run_id)

async def do_save(corpus, filename, run_id):
    """Do save operation."""
    size = save_file(corpus, filename)
    print(f"\n✅ Saved {len(corpus)} entries to '{filename}'")
    await index_corpus(corpus, run_id, i_handler)
    return make_result(True, filename, len(corpus), size)

async def handle_save_err(e, filename, run_id):
    """Handle save error."""
    if u_handler:
        return await handle_error(e, filename, run_id, u_handler)
    print(f"❌ Error saving file: {e}")
    return make_result(False)

def make_result(success, fn=None, cnt=0, sz=0):
    """Make result dict."""
    r = {'success': success}
    if success:
        r['filename'] = fn or 'corpus-content.json'
        r['entries'] = cnt
        r['file_size'] = sz
    return r

async def get_choice():
    """Get user choice."""
    print("\nOptions:")
    print("1. Use sample corpus data (5 entries)")
    print("2. Provide your own corpus data in JSON format")
    return input("\nSelect option (1 or 2): ").strip()

async def load_data(choice, run_id):
    """Load corpus data."""
    if choice == "1":
        return load_sample()
    elif choice == "2":
        return await get_loop(run_id)
    else:
        exit_invalid()

def load_sample():
    """Load sample data."""
    corpus = get_sample_data()
    print(f"\n✅ Loaded {len(corpus)} sample entries")
    return corpus

def exit_invalid():
    """Exit on invalid choice."""
    print("❌ Invalid option. Exiting...")
    sys.exit(1)

async def get_loop(run_id):
    """Loop to get user corpus."""
    while True:
        corpus = await get_user_corpus(run_id)
        if corpus:
            return corpus
        if not await retry():
            sys.exit(1)

async def retry():
    """Ask for retry."""
    print("\n⚠️  No valid corpus data collected.")
    r = input("Would you like to try again? (y/n): ").lower()
    if r != 'y':
        print("Exiting...")
        return False
    return True

async def confirm():
    """Confirm save."""
    print("\n" + "=" * 60)
    msg = "Save this corpus to 'corpus-content.json'? (y/n): "
    return input(msg).lower() == 'y'

async def save_report(corpus, run_id):
    """Save and report."""
    r = await save_corpus(corpus, "corpus-content.json", run_id)
    if r.get('success'):
        print_results(r, corpus)
    else:
        print_failure(r)

async def main():
    """Main function."""
    print_title()
    run_id = str(uuid.uuid4())
    corpus = await get_data(run_id)
    print_summary(corpus)
    await process_save(corpus, run_id)
    print("\nGoodbye! 👋")

def print_title():
    """Print title."""
    print("\n🤖 NETRA CORPUS CREATOR (with Advanced Handlers)")
    print("=" * 60)

async def get_data(run_id):
    """Get corpus data."""
    choice = await get_choice()
    return await load_data(choice, run_id)

async def process_save(corpus, run_id):
    """Process save decision."""
    if await confirm():
        await save_report(corpus, run_id)
    else:
        print("Exiting without saving...")

def run():
    """Entry point."""
    asyncio.run(main())

if __name__ == "__main__":
    run()