# Value-Based Corpus to XML Conversion Script
# Processes JSON corpus with flexible metadata and generates category-based XML files

import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional
from collections import defaultdict

def parse_json_corpus(file_path: str) -> Optional[List[Dict[str, Any]]]:
    """Reads and validates corpus data from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print(f"ERROR: JSON must contain array of entries")
            return None
        
        valid_entries = []
        for i, entry in enumerate(data):
            if all(key in entry for key in ["prompt", "response", "workload_type"]):
                valid_entries.append(entry)
            else:
                print(f"WARNING: Entry {i+1} missing required fields")
        
        print(f"SUCCESS: Loaded {len(valid_entries)} valid entries")
        return valid_entries
        
    except Exception as e:
        print(f"ERROR: Failed to process JSON: {e}")
        return None

def sanitize_filename(name: str) -> str:
    """Sanitizes category name for use as filename."""
    invalid_chars = '<>:"/\\|?*'
    sanitized = name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    return sanitized.strip() or 'uncategorized'

def get_category_from_metadata(entry: Dict[str, Any]) -> str:
    """Extracts category from metadata or returns default."""
    metadata = entry.get('metadata', {})
    category = metadata.get('category', 'General')
    return sanitize_filename(category)

def create_xml_element(entry: Dict[str, Any]) -> ET.Element:
    """Creates XML element for a single corpus entry with all fields."""
    pr_element = ET.Element("prompt_response")
    
    # Add core fields
    ET.SubElement(pr_element, "prompt").text = entry.get("prompt", "")
    ET.SubElement(pr_element, "response").text = entry.get("response", "")
    ET.SubElement(pr_element, "workload_type").text = entry.get("workload_type", "")
    
    # Add domain if present
    if "domain" in entry:
        ET.SubElement(pr_element, "domain").text = entry["domain"]
    
    # Add all metadata fields
    metadata = entry.get("metadata", {})
    if metadata:
        metadata_elem = ET.SubElement(pr_element, "metadata")
        for key, value in metadata.items():
            meta_item = ET.SubElement(metadata_elem, key)
            meta_item.text = str(value)
    
    return pr_element

def clean_xml_text(element):
    """Remove excessive whitespace from XML elements."""
    if element.text:
        element.text = element.text.strip()
    if element.tail:
        element.tail = element.tail.strip()
    for child in element:
        clean_xml_text(child)

def write_xml_file(category: str, entries: List[Dict[str, Any]], output_dir: str) -> None:
    """Appends categorized entries to XML file or creates new if doesn't exist."""
    filename = f"{category}.xml"
    filepath = os.path.join(output_dir, filename)
    
    # Check if file exists and load existing entries
    if os.path.exists(filepath):
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            # Clean up any existing whitespace issues
            clean_xml_text(root)
            existing_count = int(root.get("entry_count", "0"))
            print(f"Appending to existing {filename} ({existing_count} existing entries)")
        except:
            # If parsing fails, create new root
            root = ET.Element("corpus")
            root.set("category", category)
            existing_count = 0
    else:
        # Create new root element
        root = ET.Element("corpus")
        root.set("category", category)
        existing_count = 0
    
    # Append new entries
    for entry in entries:
        root.append(create_xml_element(entry))
    
    # Update entry count
    total_count = existing_count + len(entries)
    root.set("entry_count", str(total_count))
    
    # Clean the entire tree before writing
    clean_xml_text(root)
    
    # Pretty print XML with cleaner output
    xml_str = ET.tostring(root, 'utf-8')
    parsed_str = minidom.parseString(xml_str)
    pretty_xml = parsed_str.toprettyxml(indent="  ")
    
    # Remove excessive blank lines
    lines = pretty_xml.split('\n')
    clean_lines = [line for line in lines if line.strip() or line == '']
    clean_xml = '\n'.join(clean_lines)
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(clean_xml)
    
    action = "Updated" if existing_count > 0 else "Created"
    print(f"{action}: {filename} ({len(entries)} new, {total_count} total entries)")

def process_corpus_to_xml(input_file: str, output_dir: str = "value_corpus_xml") -> bool:
    """Main processing function for converting JSON corpus to categorized XML."""
    corpus_data = parse_json_corpus(input_file)
    if not corpus_data:
        return False
    
    # Group entries by category
    categorized_data = defaultdict(list)
    for entry in corpus_data:
        category = get_category_from_metadata(entry)
        categorized_data[category].append(entry)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nWriting XML files to '{output_dir}'...")
    
    # Write XML files for each category
    for category, entries in categorized_data.items():
        write_xml_file(category, entries, output_dir)
    
    print(f"\n✓ Generated {len(categorized_data)} XML files")
    return True

def main():
    """Main execution function."""
    input_file = "value_corpus.json"
    output_dir = "value_corpus_xml"
    
    if not os.path.exists(input_file):
        print(f"ERROR: Input file '{input_file}' not found")
        print("Please create a JSON file with corpus entries")
        return
    
    success = process_corpus_to_xml(input_file, output_dir)
    if success:
        print("\n--- CONVERSION COMPLETE ---")
        for file in sorted(os.listdir(output_dir)):
            if file.endswith('.xml'):
                print(f"  • {file}")

if __name__ == "__main__":
    main()