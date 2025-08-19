# Elite Engineer Document: Corpus to XML Conversion Script
# Date: 2024-08-19
# Author: Gemini Pro
# Updated by Claude Code: 2025-08-19 - Modified to process JSON instead of DOCX

import json
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any, Optional

# --- UTILITY FUNCTIONS ---

def parse_json_content(file_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Reads and parses corpus data from a JSON file.
    
    Args:
        file_path: The path to the JSON file.

    Returns:
        A list of dictionaries representing the corpus data, or None on error.
    """
    print(f"INFO: Reading content from '{file_path}'...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate it's a list
        if not isinstance(data, list):
            print("ERROR: JSON file must contain an array of corpus entries.")
            return None
        
        # Validate each entry has required fields
        valid_entries = []
        for i, entry in enumerate(data):
            if all(key in entry for key in ["prompt", "response", "workload_type"]):
                valid_entries.append(entry)
            else:
                print(f"WARNING: Entry {i + 1} missing required fields, skipping.")
        
        print(f"SUCCESS: Loaded {len(valid_entries)} valid records from the JSON file.")
        return valid_entries

    except FileNotFoundError:
        print(f"ERROR: The file '{file_path}' was not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to decode JSON from the file. Details: {e}")
        return None
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while processing the JSON file: {e}")
        return None

def get_update_frequency(workload_type: str) -> str:
    """
    Maps a workload_type to its corresponding update frequency based on
    pre-defined engineering assumptions.
    
    Args:
        workload_type: The workload type from the source data.
        
    Returns:
        The categorized frequency ('static', 'occasional', 'dynamic').
    """
    frequency_map = {
        "failed_request": "static",      # Policy-based, changes rarely.
        "tool_use": "static",            # Links are generally stable.
        "simple_chat": "occasional",     # General info, updated periodically.
        "rag_pipeline": "dynamic"        # RAG content can change frequently.
    }
    return frequency_map.get(workload_type, "static") # Default to static.

def get_domain(prompt: str, response: str, workload_type: str) -> str:
    """
    Categorizes a prompt into a high-level domain based on its content
    and workload type. The rules are applied with precedence.
    
    Args:
        prompt: The prompt text.
        response: The response text.
        workload_type: The workload type.
        
    Returns:
        The categorized domain string.
    """
    prompt_lower = prompt.lower()
    
    # Precedence 1: Suspicious content
    if workload_type == "failed_request":
        return "suspicious-general"
    
    # Precedence 2: Responses containing links
    if "https://" in response or "http://" in response:
        return "netra-links"
        
    # Precedence 3: Keyword-based matching
    domain_keywords = {
        "netra-pricing": ["pricing", "cost", "free tier", "plans", "subscription", "upgrade"],
        "netra-security": ["security", "pii", "compliant", "soc 2", "hipaa", "access control"],
        "netra-strategy": ["mission", "differentiate", "roi", "time-to-market", "scaling", "use case", "benefits"],
        "netra-ai-optimization": ["optimization", "caching", "model routing", "prompt", "agentic", "observability"]
    }

    for domain, keywords in domain_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            return domain
            
    # Precedence 4: Default catch-all
    return "netra-general"

# --- MAIN EXECUTION ---

def main():
    """Main function to run the end-to-end conversion process."""
    source_file = 'corpus-content.json'
    output_directory = "categorized_xml_output"

    corpus_data = parse_json_content(source_file)
    if not corpus_data:
        print("FATAL: Could not process the source file. XML generation aborted.")
        return

    # In-memory data structure for categorization
    categorized_data = {}

    for item in corpus_data:
        prompt = item.get("prompt")
        response = item.get("response")
        workload_type = item.get("workload_type")

        if not all([prompt, response, workload_type]):
            continue # Skip malformed records

        domain = get_domain(prompt, response, workload_type)
        frequency = get_update_frequency(workload_type)
        
        # Apply special rule: suspicious content is always static.
        if domain == "suspicious-general":
            frequency = "static"

        key = (domain, frequency)
        if key not in categorized_data:
            categorized_data[key] = []
        
        categorized_data[key].append({"prompt": prompt, "response": response})
    
    # Create XML files from categorized data
    os.makedirs(output_directory, exist_ok=True)
    print(f"INFO: Writing XML files to the '{output_directory}' directory...")

    for (domain, frequency), data in categorized_data.items():
        # Create root element with metadata attributes
        root = ET.Element("corpus")
        root.set("domain", domain)
        root.set("update_frequency", frequency)

        for pr_pair in data:
            pr_element = ET.SubElement(root, "prompt_response")
            ET.SubElement(pr_element, "prompt").text = pr_pair["prompt"]
            ET.SubElement(pr_element, "response").text = pr_pair["response"]
        
        # Use minidom for pretty-printing the XML
        xml_str = ET.tostring(root, 'utf-8')
        parsed_str = minidom.parseString(xml_str)
        pretty_xml = parsed_str.toprettyxml(indent="  ")

        file_name = f"{domain}-{frequency}.xml"
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(pretty_xml)
            
    print("\n--- EXECUTION COMPLETE ---")
    print("SUCCESS: The following XML files have been generated:")
    for file in sorted(os.listdir(output_directory)):
        print(f"- {file}")

if __name__ == "__main__":
    main()