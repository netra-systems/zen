#!/usr/bin/env python3
"""
Script to identify legacy SPECs and add last_edited timestamps to all SPEC files.
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import re

# Define patterns that indicate legacy/outdated specs
LEGACY_INDICATORS = [
    # Old naming patterns
    r'_old\.xml$',
    r'_backup\.xml$',
    r'_deprecated\.xml$',
    r'_legacy\.xml$',
    
    # Content patterns (will check in content)
    r'DEPRECATED',
    r'OBSOLETE',
    r'DO NOT USE',
    r'LEGACY',
    r'OLD VERSION',
    r'REPLACED BY',
    r'SUPERSEDED',
    
    # Old architectural patterns
    r'monolithic',
    r'single-service',
    
    # Files in archived folders
    r'archived_implementations',
    r'archived',
    r'old',
    r'legacy',
    r'deprecated',
]

# SPECs that are known to be current/active (from CLAUDE.md references)
ACTIVE_SPECS = {
    'type_safety.xml',
    'conventions.xml',
    'code_changes.xml',
    'no_test_stubs.xml',
    'anti_regression.xml',
    'independent_services.xml',
    'string_literals_index.xml',
    'testing.xml',
    'coverage_requirements.xml',
    'clickhouse.xml',
    'postgres.xml',
    'websockets.xml',
    'websocket_communication.xml',
    'security.xml',
    'PRODUCTION_SECRETS_ISOLATION.xml',
    'github_actions.xml',
    'ai_factory_patterns.xml',
    'system_boundaries.xml',
    'growth_control.xml',
    'test_runner_guide.xml',
    'master_wip_index.xml',
    'ai_factory_status_report.xml',
    'compliance_reporting.xml',
    'test_reporting.xml',
}

# SPECs that appear to be old UI/frontend related (likely legacy)
LEGACY_UI_PATTERNS = [
    'ui_ux_',  # Old UI patterns
    'frontend_layout',  # Old frontend structure
    'marketing-page',  # Old marketing page
    'unified_chat_ui_ux',  # Old chat UI
]

def is_legacy_spec(file_path: Path, content: str = None) -> Tuple[bool, List[str]]:
    """
    Determine if a SPEC file is legacy based on various indicators.
    
    Returns:
        Tuple of (is_legacy: bool, reasons: List[str])
    """
    reasons = []
    file_str = str(file_path)
    filename = file_path.name
    
    # Check if in archived folder
    if any(folder in file_str for folder in ['archived', 'archived_implementations', 'old', 'legacy']):
        reasons.append(f"In archived/legacy folder")
    
    # Check filename patterns
    for pattern in LEGACY_INDICATORS[:4]:  # First 4 are filename patterns
        if re.search(pattern, filename, re.IGNORECASE):
            reasons.append(f"Filename matches legacy pattern: {pattern}")
    
    # Check for old UI patterns
    for ui_pattern in LEGACY_UI_PATTERNS:
        if ui_pattern in filename.lower():
            reasons.append(f"Old UI/frontend pattern: {ui_pattern}")
    
    # Check content if provided
    if content:
        for pattern in LEGACY_INDICATORS[4:]:  # Rest are content patterns
            if re.search(pattern, content, re.IGNORECASE):
                reasons.append(f"Content contains: {pattern}")
        
        # Check for references to old systems
        if 'single service' in content.lower() or 'monolithic' in content.lower():
            reasons.append("References old monolithic architecture")
        
        # Check for old business models or tiers
        if any(term in content.lower() for term in ['freemium', 'basic tier', 'premium tier']):
            if 'free tier' not in content.lower():  # Current model uses Free/Early/Mid/Enterprise
                reasons.append("References old business model tiers")
    
    # Files with these names but not in ACTIVE_SPECS are likely outdated
    outdated_likely = [
        'Status.xml',  # Old status tracking
        'history.xml',  # Historical info
        'review.xml',  # Old review process
        'doc_overall.xml',  # Old documentation
        'e2e-demo.xml',  # Old demo
        'swimlane.xml',  # Old process diagram
        'selfchecks.xml',  # Old validation
        'instructions.xml',  # Old instructions (replaced by CLAUDE.md)
        'types.xml',  # Old type definitions
        'data.xml',  # Generic old data spec
        'core.xml',  # Generic old core spec
        'services.xml',  # Old services spec
        'database.xml',  # Generic old database spec (replaced by postgres.xml, clickhouse.xml)
        'architecture.xml',  # Old architecture (replaced by system_boundaries.xml, etc)
    ]
    
    if filename in outdated_likely and filename not in ACTIVE_SPECS:
        reasons.append(f"Likely outdated spec: {filename}")
    
    return len(reasons) > 0, reasons

def add_timestamp_to_xml(file_path: Path, is_legacy: bool = False, legacy_reasons: List[str] = None):
    """
    Add or update last_edited timestamp in XML file.
    Also adds legacy status if applicable.
    """
    try:
        # Parse XML
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Get current timestamp
        now = datetime.now().isoformat()
        
        # Check if metadata element exists
        metadata = root.find('metadata')
        if metadata is None:
            # Create metadata element as first child
            metadata = ET.Element('metadata')
            root.insert(0, metadata)
        
        # Check for existing last_edited
        last_edited = metadata.find('last_edited')
        if last_edited is None:
            # Add last_edited element
            last_edited = ET.SubElement(metadata, 'last_edited')
            last_edited.text = now
        # If no existing timestamp, set to now
        elif not last_edited.text or last_edited.text.strip() == '':
            last_edited.text = now
        
        # Add legacy status if applicable
        if is_legacy:
            legacy_elem = metadata.find('legacy_status')
            if legacy_elem is None:
                legacy_elem = ET.SubElement(metadata, 'legacy_status')
            
            legacy_elem.set('is_legacy', 'true')
            legacy_elem.set('identified_date', now)
            
            # Add reasons
            reasons_elem = legacy_elem.find('reasons')
            if reasons_elem is not None:
                legacy_elem.remove(reasons_elem)
            reasons_elem = ET.SubElement(legacy_elem, 'reasons')
            
            for reason in legacy_reasons or []:
                reason_elem = ET.SubElement(reasons_elem, 'reason')
                reason_elem.text = reason
        
        # Format and write back
        ET.indent(tree, space='  ')
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        
        return True
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all SPEC files."""
    
    # Get SPEC directory
    spec_dir = Path('SPEC')
    if not spec_dir.exists():
        print("Error: SPEC directory not found!")
        return
    
    # Find all XML files
    xml_files = list(spec_dir.rglob('*.xml'))
    
    print(f"Found {len(xml_files)} XML files in SPEC directory\n")
    
    # Track statistics
    stats = {
        'total': len(xml_files),
        'legacy': 0,
        'active': 0,
        'updated': 0,
        'errors': 0
    }
    
    legacy_specs = []
    active_specs_list = []
    
    # Process each file
    for xml_file in xml_files:
        try:
            # Read content for analysis
            content = xml_file.read_text(encoding='utf-8')
            
            # Check if legacy
            is_legacy, reasons = is_legacy_spec(xml_file, content)
            
            # Check if explicitly active
            is_active = xml_file.name in ACTIVE_SPECS
            
            if is_legacy:
                stats['legacy'] += 1
                legacy_specs.append((xml_file, reasons))
                print(f"LEGACY: {xml_file.relative_to(spec_dir)}")
                for reason in reasons:
                    print(f"  - {reason}")
            elif is_active:
                stats['active'] += 1
                active_specs_list.append(xml_file)
                print(f"ACTIVE: {xml_file.relative_to(spec_dir)}")
            else:
                print(f"UNKNOWN: {xml_file.relative_to(spec_dir)}")
            
            # Add timestamp to file
            if add_timestamp_to_xml(xml_file, is_legacy, reasons):
                stats['updated'] += 1
            else:
                stats['errors'] += 1
                
        except Exception as e:
            print(f"Error processing {xml_file}: {e}")
            stats['errors'] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total SPEC files: {stats['total']}")
    print(f"Legacy SPECs identified: {stats['legacy']}")
    print(f"Active SPECs: {stats['active']}")
    print(f"Unknown status: {stats['total'] - stats['legacy'] - stats['active']}")
    print(f"Files updated: {stats['updated']}")
    print(f"Errors: {stats['errors']}")
    
    # Create legacy specs report
    report_path = Path('SPEC/legacy_specs_report.md')
    with open(report_path, 'w') as f:
        f.write("# Legacy SPECs Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total SPEC files: {stats['total']}\n")
        f.write(f"- Legacy SPECs: {stats['legacy']}\n")
        f.write(f"- Active SPECs: {stats['active']}\n")
        f.write(f"- Unknown status: {stats['total'] - stats['legacy'] - stats['active']}\n\n")
        
        f.write("## Legacy SPECs\n\n")
        f.write("The following SPECs have been identified as legacy/outdated:\n\n")
        
        for spec_file, reasons in legacy_specs:
            f.write(f"### {spec_file.relative_to(spec_dir)}\n")
            f.write("**Reasons:**\n")
            for reason in reasons:
                f.write(f"- {reason}\n")
            f.write("\n")
        
        f.write("## Recommended Actions\n\n")
        f.write("1. Review legacy SPECs and determine if they should be:\n")
        f.write("   - Archived (moved to archived folder)\n")
        f.write("   - Deleted (if truly obsolete)\n")
        f.write("   - Updated (if still relevant but outdated)\n\n")
        f.write("2. Update LLM_MASTER_INDEX.md to reflect current state\n")
        f.write("3. Consider consolidating related SPECs\n")
        f.write("4. Update CLAUDE.md references if needed\n")
    
    print(f"\nReport written to: {report_path}")

if __name__ == "__main__":
    main()