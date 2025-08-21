#!/usr/bin/env python3
"""Interactive script for creating value-based corpus with metadata."""

import json
import os
import sys
from typing import Any, Dict, List

from netra_backend.app.agents.corpus_admin.value_based_corpus.value_corpus_to_xml import (
    process_corpus_to_xml,
)
from netra_backend.app.agents.corpus_admin.value_based_corpus.value_corpus_validation import (
    validate_sync,
)


def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with optional default."""
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()

def create_corpus_entry() -> Dict[str, Any]:
    """Create a single corpus entry interactively with validation."""
    print("\n--- New Corpus Entry ---")
    
    # Required fields
    prompt = get_user_input("Enter prompt")
    response = get_user_input("Enter response")
    workload_type = get_user_input("Enter workload_type", "simple_chat")
    
    # Optional domain
    domain = get_user_input("Enter domain (optional)")
    
    # Build entry
    entry = {
        "prompt": prompt,
        "response": response,
        "workload_type": workload_type
    }
    
    if domain:
        entry["domain"] = domain
    
    # Optional metadata
    if input("\nAdd metadata? (y/n): ").lower() == 'y':
        metadata = {}
        
        # Always ask for category first
        category = get_user_input("Enter category", "General")
        metadata["category"] = category
        
        # Additional metadata fields
        while True:
            key = get_user_input("\nMetadata key (or press Enter to finish)")
            if not key:
                break
            value = get_user_input(f"Value for '{key}'")
            metadata[key] = value
        
        if metadata:
            entry["metadata"] = metadata
    
    # Validate the entry
    valid, errors = validate_sync([entry])
    if errors:
        print("\n⚠ Validation errors found:")
        for error in errors:
            print(f"  • {error}")
        if input("\nTry again? (y/n): ").lower() == 'y':
            return create_corpus_entry()
        return None
    
    return entry

def load_existing_corpus(filepath: str) -> List[Dict[str, Any]]:
    """Load existing corpus from file."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            print("Could not load existing corpus, starting fresh")
    return []

def save_corpus(corpus: List[Dict[str, Any]], filepath: str) -> None:
    """Save corpus to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Saved {len(corpus)} entries to {filepath}")

def display_entry(entry: Dict[str, Any], index: int) -> None:
    """Display a corpus entry."""
    print(f"\n--- Entry {index} ---")
    print(f"Prompt: {entry.get('prompt', '')[:100]}...")
    print(f"Response: {entry.get('response', '')[:100]}...")
    print(f"Workload Type: {entry.get('workload_type', '')}")
    
    if 'domain' in entry:
        print(f"Domain: {entry['domain']}")
    
    if 'metadata' in entry:
        print("Metadata:")
        for key, value in entry['metadata'].items():
            print(f"  {key}: {value}")

def import_json_list() -> List[Dict[str, Any]]:
    """Import a list of JSON entries from file or paste with automatic validation."""
    print("\n--- Import JSON List ---")
    print("1. Import from file")
    print("2. Paste JSON data")
    
    choice = input("\nChoice: ").strip()
    
    data = []
    
    if choice == "1":
        filepath = get_user_input("Enter JSON file path")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print("Error: File must contain a JSON array")
                    return []
                print(f"✓ Loaded {len(data)} entries from file")
        except FileNotFoundError:
            print(f"Error: File '{filepath}' not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON - {e}")
            return []
    
    elif choice == "2":
        print("Paste JSON array (press Enter twice when done):")
        lines = []
        empty_count = 0
        while True:
            line = input()
            if not line:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
                lines.append(line)
        
        json_text = '\n'.join(lines)
        try:
            data = json.loads(json_text)
            if not isinstance(data, list):
                print("Error: Input must be a JSON array")
                return []
            print(f"✓ Parsed {len(data)} entries")
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON - {e}")
            return []
    else:
        return []
    
    # Validate entries immediately
    print("\nValidating entries...")
    valid, errors = validate_sync(data)
    
    if errors:
        print(f"\n⚠ Validation found issues:")
        for error in errors[:10]:
            print(f"  • {error}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        
        if not valid:
            print("\n✗ No valid entries found. Import cancelled.")
            return []
        
        print(f"\n{len(valid)} of {len(data)} entries are valid.")
        if input("Import only valid entries? (y/n): ").lower() != 'y':
            print("Import cancelled.")
            return []
    else:
        print(f"✓ All {len(data)} entries are valid")
    
    return valid

def main():
    """Main interactive loop."""
    print("=== Value-Based Corpus Creator ===")
    print("Create corpus entries with flexible metadata\n")
    
    corpus_file = "value_corpus.json"
    corpus = load_existing_corpus(corpus_file)
    
    if corpus:
        print(f"Loaded {len(corpus)} existing entries")
    
    while True:
        print("\nOptions:")
        print("1. Add single entry")
        print("2. Import JSON list")
        print("3. View entries")
        print("4. Generate XML files")
        print("5. Save and exit")
        print("6. Exit without saving")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            entry = create_corpus_entry()
            if entry:
                corpus.append(entry)
                print(f"\n✓ Added entry (total: {len(corpus)})")
            else:
                print("Entry not added.")
            
        elif choice == "2":
            imported_entries = import_json_list()
            if imported_entries:
                corpus.extend(imported_entries)
                print(f"✓ Added {len(imported_entries)} entries (total: {len(corpus)})")
            
        elif choice == "3":
            if not corpus:
                print("No entries yet")
            else:
                for i, entry in enumerate(corpus, 1):
                    display_entry(entry, i)
                    
        elif choice == "4":
            if not corpus:
                print("No entries to convert")
            else:
                save_corpus(corpus, corpus_file)
                success = process_corpus_to_xml(corpus_file)
                if success:
                    print("\n✓ XML files generated successfully")
                    # Clear the JSON file after successful XML generation
                    corpus.clear()
                    save_corpus([], corpus_file)
                    print("✓ Cleared value_corpus.json")
                    
        elif choice == "5":
            save_corpus(corpus, corpus_file)
            print("\nGoodbye!")
            break
            
        elif choice == "6":
            if input("Exit without saving? (y/n): ").lower() == 'y':
                print("\nGoodbye!")
                break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()