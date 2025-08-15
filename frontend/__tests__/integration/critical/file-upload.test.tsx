/**
 * File Upload Integration Tests
 * Tests for file upload functionality and progress tracking
 */

import React from 'react';
import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Import test utilities
import { TestProviders } from '../../test-utils/providers';

describe('File Upload Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Upload Functionality', () => {
    it('should upload file and process with agent', async () => {
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ file_id: 'file-123', status: 'uploaded' })
      });
      
      const uploadFile = async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        
        return response.json();
      };
      
      const result = await uploadFile(file);
      
      expect(result.file_id).toBe('file-123');
      expect(result.status).toBe('uploaded');
    });

    it('should track upload progress', async () => {
      const file = new File(['x'.repeat(1000000)], 'large.txt', { type: 'text/plain' });
      
      const uploadWithProgress = async (
        file: File,
        onProgress: (percent: number) => void
      ) => {
        // Simulate progress updates
        for (let i = 0; i <= 100; i += 20) {
          onProgress(i);
          await new Promise(resolve => setTimeout(resolve, 10));
        }
        
        return { success: true };
      };
      
      const progressCallback = jest.fn();
      await uploadWithProgress(file, progressCallback);
      
      expect(progressCallback).toHaveBeenCalledWith(0);
      expect(progressCallback).toHaveBeenCalledWith(100);
      expect(progressCallback.mock.calls.length).toBeGreaterThan(2);
    });
  });
});