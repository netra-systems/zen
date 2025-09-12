#!/usr/bin/env python3
"""Robust splitting of learnings.xml into modular files."""

import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


def extract_learnings(content: str) -> List[Tuple[str, str, str]]:
    """Extract learning blocks with ID, category, and content."""
    learnings = []
    
    # Pattern to match learning blocks
    pattern = r'<learning id="([^"]+)">(.*?)</learning>'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for learning_id, learning_content in matches:
        # Extract category
        cat_match = re.search(r'<category>([^<]+)</category>', learning_content)
        category = cat_match.group(1).strip() if cat_match else 'Uncategorized'
        
        # Create full learning block
        full_block = f'<learning id="{learning_id}">{learning_content}</learning>'
        
        learnings.append((learning_id, category, full_block))
    
    return learnings

def sanitize_filename(name: str) -> str:
    """Convert category name to valid filename."""
    name = name.replace('/', '_')
    name = name.lower().replace(' ', '_')
    name = re.sub(r'[^a-z0-9_]', '', name)
    return name

def escape_xml(text: str) -> str:
    """Escape XML special characters."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&apos;')
    return text

def create_category_file(category: str, learnings: List[Tuple[str, str]], 
                         output_dir: Path) -> str:
    """Create XML file for a category."""
    filename = f"{sanitize_filename(category)}.xml"
    filepath = output_dir / filename
    
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_content.append('<specification>')
    xml_content.append('    <metadata>')
    xml_content.append(f'        <name>Learnings - {category}</name>')
    xml_content.append('        <type>learnings</type>')
    xml_content.append(f'        <category>{category}</category>')
    xml_content.append('        <version>1.0</version>')
    xml_content.append('        <last_updated>2025-08-16</last_updated>')
    xml_content.append(f'        <description>Learnings and fixes for {category}</description>')
    xml_content.append('    </metadata>')
    xml_content.append('    ')
    xml_content.append('    <learnings>')
    
    for learning_id, content in learnings:
        # Indent the learning content
        indented = '\n'.join('        ' + line if line.strip() else '' 
                           for line in content.split('\n'))
        xml_content.append(indented)
        xml_content.append('')
    
    xml_content.append('    </learnings>')
    xml_content.append('</specification>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_content))
    
    return filename

def create_index(categories: Dict[str, List[str]], output_dir: Path):
    """Create index.xml with all categories and files."""
    xml_content = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_content.append('<specification>')
    xml_content.append('    <metadata>')
    xml_content.append('        <name>Learnings Index</name>')
    xml_content.append('        <type>index</type>')
    xml_content.append('        <version>1.0</version>')
    xml_content.append('        <last_updated>2025-08-16</last_updated>')
    xml_content.append('        <description>Index of all learning modules organized by category</description>')
    xml_content.append('    </metadata>')
    xml_content.append('    ')
    xml_content.append('    <categories>')
    
    for category in sorted(categories.keys()):
        filename = f"{sanitize_filename(category)}.xml"
        learning_ids = categories[category]
        
        xml_content.append('        <category>')
        xml_content.append(f'            <name>{category}</name>')
        xml_content.append(f'            <file>learnings/{filename}</file>')
        xml_content.append(f'            <path>SPEC/learnings/{filename}</path>')
        xml_content.append(f'            <learning_count>{len(learning_ids)}</learning_count>')
        xml_content.append('            <learning_ids>')
        for lid in learning_ids:
            xml_content.append(f'                <id>{lid}</id>')
        xml_content.append('            </learning_ids>')
        xml_content.append('        </category>')
    
    xml_content.append('    </categories>')
    xml_content.append('    ')
    xml_content.append('    <usage>')
    xml_content.append('        <instruction>Each category file contains related learnings and troubleshooting patterns</instruction>')
    xml_content.append('        <instruction>Search specific category files for targeted fixes and solutions</instruction>')
    xml_content.append('        <instruction>Check index.xml for complete category listing and learning IDs</instruction>')
    xml_content.append('        <instruction>Use learning IDs to quickly find specific fixes across categories</instruction>')
    xml_content.append('    </usage>')
    xml_content.append('    ')
    xml_content.append('    <statistics>')
    xml_content.append(f'        <total_categories>{len(categories)}</total_categories>')
    xml_content.append(f'        <total_learnings>{sum(len(ids) for ids in categories.values())}</total_learnings>')
    xml_content.append('    </statistics>')
    xml_content.append('</specification>')
    
    with open(output_dir / 'index.xml', 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_content))

def main():
    """Main function to split learnings."""
    spec_dir = Path(r'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\SPEC')
    learnings_file = spec_dir / 'learnings.xml'
    output_dir = spec_dir / 'learnings'
    
    # Read the file
    print(f"Reading {learnings_file}...")
    with open(learnings_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract learnings
    print("Extracting learnings...")
    all_learnings = extract_learnings(content)
    print(f"Found {len(all_learnings)} learnings")
    
    # Group by category
    learnings_by_category = defaultdict(list)
    for learning_id, category, content in all_learnings:
        learnings_by_category[category].append((learning_id, content))
    
    # Create category files
    category_info = {}
    for category, learnings in learnings_by_category.items():
        print(f"Creating file for {category} ({len(learnings)} learnings)...")
        filename = create_category_file(category, learnings, output_dir)
        category_info[category] = [lid for lid, _ in learnings]
    
    # Create index
    print("Creating index.xml...")
    create_index(category_info, output_dir)
    
    print(f"\n PASS:  Successfully created {len(category_info)} category files:")
    for cat in sorted(category_info.keys()):
        filename = f"{sanitize_filename(cat)}.xml"
        print(f"  - {cat}: {filename} ({len(category_info[cat])} learnings)")
    
    print(f"\n[U+1F4CB] Index created at: SPEC/learnings/index.xml")

if __name__ == '__main__':
    main()