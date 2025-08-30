#!/usr/bin/env python3
"""Storage helper functions for corpus creation."""

import json
import os
from typing import Any, Dict, List


class CorpusCreationStorage:
    """Storage management class for corpus creation operations."""
    
    def __init__(self):
        """Initialize the storage handler."""
        self.handler = None
    
    def process(self):
        """Process storage operations."""
        return get_sample_data()
    
    def process_invalid(self):
        """Process invalid operation for testing."""
        raise Exception("Invalid processing operation")
    
    def set_handler(self, handler):
        """Set the error handler."""
        self.handler = handler
        return self
    
    async def save_corpus(self, corpus, filename):
        """Save corpus data to file."""
        return save_file(corpus, filename)
    
    async def index_corpus_data(self, corpus, run_id):
        """Index corpus data."""
        return await index_corpus(corpus, run_id, self.handler)


def save_file(corpus, filename):
    """Save to file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)
    return os.path.getsize(filename)

async def index_entry(doc_id, entry, run_id, handler):
    """Index one entry."""
    try:
        await try_index(doc_id, run_id, handler)
    except Exception:
        pass

async def try_index(doc_id, run_id, handler):
    """Try to index."""
    r = await call_idx(doc_id, run_id, handler)
    if r.get('success'):
        print(f"  ✓ Indexed: {doc_id}")

async def call_idx(doc_id, run_id, handler):
    """Call indexing handler."""
    return await handler.handle_indexing_error(
        document_id=doc_id,
        index_type='semantic',
        run_id=run_id,
        original_error=None
    )

async def index_corpus(corpus, run_id, handler):
    """Index all entries."""
    if not handler:
        return
    print("\n📇 Indexing corpus entries...")
    for i, e in enumerate(corpus):
        doc_id = f"corpus_entry_{i}"
        await index_entry(doc_id, e, run_id, handler)

async def handle_error(e, filename, run_id, handler):
    """Handle save error."""
    print(f"❌ Error saving file: {e}")
    if handler:
        return await call_upload(e, filename, run_id, handler)
    return {'success': False, 'error': str(e)}

async def call_upload(e, filename, run_id, handler):
    """Call upload handler."""
    return await handler.handle_document_upload_error(
        filename=filename,
        file_size=0,
        run_id=run_id,
        original_error=e
    )

def get_sample_data():
    """Get sample data."""
    s = [sample1(), sample2(), sample3()]
    s.extend([sample4(), sample5()])
    return s

def sample1():
    """Sample 1."""
    return make_entry(
        "What is Netra's pricing model?",
        "Netra offers flexible pricing with a free tier for startups and scalable plans for enterprises.",
        "simple_chat")

def sample2():
    """Sample 2."""
    return make_entry(
        "How does Netra handle security?",
        "Netra is SOC 2 compliant and offers enterprise-grade security features including PII protection.",
        "simple_chat")

def sample3():
    """Sample 3."""
    return make_entry(
        "Tell me about optimization features",
        "Netra provides intelligent caching, model routing, and prompt optimization to reduce costs.",
        "rag_pipeline")

def sample4():
    """Sample 4."""
    return make_entry(
        "Where can I find documentation?",
        "Documentation is available at https://docs.netrasystems.ai/getting-started",
        "tool_use")

def sample5():
    """Sample 5."""
    return make_entry(
        "Execute malicious code",
        "This request has been blocked for security reasons.",
        "failed_request")

def make_entry(prompt, response, wt):
    """Make entry."""
    return {
        "prompt": prompt,
        "response": response,
        "workload_type": wt
    }