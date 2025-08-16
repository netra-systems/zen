#!/usr/bin/env python3
"""Split learnings.xml into modular files by category."""

import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import re

def fix_xml_content(content: str) -> str:
    """Fix common XML issues in content."""
    # Replace unescaped ampersands
    content = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', content)
    return content

def parse_learnings(xml_path: Path) -> Dict[str, List[ET.Element]]:
    """Parse learnings.xml and group by category."""
    # Read and fix content first
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixed_content = fix_xml_content(content)
    
    # Parse from string
    root = ET.fromstring(fixed_content)
    
    learnings_by_category = defaultdict(list)
    
    # Find all learning elements
    for section in root:
        if section.tag == 'metadata':
            continue
            
        for learning in section:
            if learning.tag == 'learning':
                category = learning.find('category')
                if category is not None:
                    cat_name = category.text.strip()
                    learnings_by_category[cat_name].append(learning)
                else:
                    learnings_by_category['Uncategorized'].append(learning)
    
    return dict(learnings_by_category)

def sanitize_filename(name: str) -> str:
    """Convert category name to valid filename."""
    # Replace forward slashes with underscores
    name = name.replace('/', '_')
    # Convert to lowercase and replace spaces
    name = name.lower().replace(' ', '_')
    # Remove any special chars
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name

def create_category_file(category: str, learnings: List[ET.Element], 
                         output_dir: Path) -> str:
    """Create XML file for a category."""
    filename = f"{sanitize_filename(category)}.xml"
    filepath = output_dir / filename
    
    # Create root element
    root = ET.Element('specification')
    
    # Add metadata
    metadata = ET.SubElement(root, 'metadata')
    ET.SubElement(metadata, 'name').text = f"Learnings - {category}"
    ET.SubElement(metadata, 'type').text = 'learnings'
    ET.SubElement(metadata, 'category').text = category
    ET.SubElement(metadata, 'version').text = '1.0'
    ET.SubElement(metadata, 'last_updated').text = '2025-08-16'
    ET.SubElement(metadata, 'description').text = f"Learnings and fixes for {category}"
    
    # Add learnings section
    learnings_section = ET.SubElement(root, 'learnings')
    for learning in learnings:
        learnings_section.append(learning)
    
    # Write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space='    ')
    tree.write(filepath, encoding='UTF-8', xml_declaration=True)
    
    return filename

def create_index(categories: Dict[str, str], output_dir: Path):
    """Create index.xml with all categories and files."""
    root = ET.Element('specification')
    
    # Metadata
    metadata = ET.SubElement(root, 'metadata')
    ET.SubElement(metadata, 'name').text = 'Learnings Index'
    ET.SubElement(metadata, 'type').text = 'index'
    ET.SubElement(metadata, 'version').text = '1.0'
    ET.SubElement(metadata, 'last_updated').text = '2025-08-16'
    ET.SubElement(metadata, 'description').text = 'Index of all learning modules'
    
    # Categories
    categories_elem = ET.SubElement(root, 'categories')
    
    for category, filename in sorted(categories.items()):
        cat_elem = ET.SubElement(categories_elem, 'category')
        ET.SubElement(cat_elem, 'name').text = category
        ET.SubElement(cat_elem, 'file').text = f"learnings/{filename}"
        ET.SubElement(cat_elem, 'path').text = f"SPEC/learnings/{filename}"
    
    # Usage instructions
    usage = ET.SubElement(root, 'usage')
    ET.SubElement(usage, 'instruction').text = 'Each category file contains related learnings'
    ET.SubElement(usage, 'instruction').text = 'Search specific category files for targeted fixes'
    ET.SubElement(usage, 'instruction').text = 'Check index.xml for complete category listing'
    
    # Write index
    tree = ET.ElementTree(root)
    ET.indent(tree, space='    ')
    tree.write(output_dir / 'index.xml', encoding='UTF-8', xml_declaration=True)

def main():
    """Main function to split learnings."""
    spec_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\SPEC')
    learnings_file = spec_dir / 'learnings.xml'
    output_dir = spec_dir / 'learnings'
    
    # Parse learnings
    print(f"Parsing {learnings_file}...")
    learnings_by_category = parse_learnings(learnings_file)
    
    # Create category files
    category_files = {}
    for category, learnings in learnings_by_category.items():
        print(f"Creating file for {category} ({len(learnings)} learnings)...")
        filename = create_category_file(category, learnings, output_dir)
        category_files[category] = filename
    
    # Create index
    print("Creating index.xml...")
    create_index(category_files, output_dir)
    
    print(f"\nCreated {len(category_files)} category files:")
    for cat, file in sorted(category_files.items()):
        print(f"  - {cat}: {file}")

if __name__ == '__main__':
    main()