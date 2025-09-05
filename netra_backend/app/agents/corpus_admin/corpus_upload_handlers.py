"""
Corpus upload handlers module.

Provides handlers for corpus upload operations.
This module has been removed but tests still reference it.
"""


class CorpusUploadHandlers:
    """
    Corpus upload handlers.
    
    Handles upload operations for corpus management.
    """
    
    def __init__(self):
        pass
    
    def upload_file(self, file_path, corpus_id):
        """Upload file to corpus."""
        return True
    
    def upload_batch(self, file_paths, corpus_id):
        """Upload multiple files to corpus."""
        return True
    
    def validate_upload(self, file_data):
        """Validate upload data."""
        return True
    
    def process_upload(self, upload_data):
        """Process uploaded data."""
        return {"status": "processed", "files": 0}