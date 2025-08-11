import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CorpusAdmin } from '@/components/CorpusAdmin';
// Using Jest, not vitest

// Mock API calls
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('test_CorpusAdmin_management', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('should render corpus management UI correctly', () => {
    render(<CorpusAdmin />);
    
    expect(screen.getByText(/Corpus Management/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add Document/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Bulk Import/i })).toBeInTheDocument();
  });

  it('should handle bulk operations', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ documents: [] }),
    });

    render(<CorpusAdmin />);
    
    const bulkImportButton = screen.getByRole('button', { name: /Bulk Import/i });
    fireEvent.click(bulkImportButton);

    await waitFor(() => {
      expect(screen.getByText(/Select files to import/i)).toBeInTheDocument();
    });

    const fileInput = screen.getByLabelText(/Select files/i);
    const files = [
      new File(['content1'], 'doc1.txt', { type: 'text/plain' }),
      new File(['content2'], 'doc2.txt', { type: 'text/plain' }),
    ];
    
    await userEvent.upload(fileInput, files);

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, imported: 2 }),
    });

    const uploadButton = screen.getByRole('button', { name: /Upload/i });
    fireEvent.click(uploadButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/corpus/bulk-import'),
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  it('should handle document deletion', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        documents: [
          { id: '1', name: 'Document 1', size: 1024 },
          { id: '2', name: 'Document 2', size: 2048 },
        ],
      }),
    });

    render(<CorpusAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Document 1')).toBeInTheDocument();
      expect(screen.getByText('Document 2')).toBeInTheDocument();
    });

    const deleteButton = screen.getAllByRole('button', { name: /Delete/i })[0];
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true }),
    });

    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/corpus/1'),
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });

  it('should handle search functionality', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        documents: [
          { id: '1', name: 'Technical Guide', size: 1024 },
          { id: '2', name: 'User Manual', size: 2048 },
        ],
      }),
    });

    render(<CorpusAdmin />);

    const searchInput = screen.getByPlaceholderText(/Search documents/i);
    await userEvent.type(searchInput, 'Technical');

    await waitFor(() => {
      expect(screen.getByText('Technical Guide')).toBeInTheDocument();
      expect(screen.queryByText('User Manual')).not.toBeInTheDocument();
    });
  });

  it('should display document details on selection', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        documents: [
          { 
            id: '1', 
            name: 'Document 1', 
            size: 1024,
            created: '2025-01-01T00:00:00Z',
            modified: '2025-01-02T00:00:00Z',
          },
        ],
      }),
    });

    render(<CorpusAdmin />);

    await waitFor(() => {
      expect(screen.getByText('Document 1')).toBeInTheDocument();
    });

    const document = screen.getByText('Document 1');
    fireEvent.click(document);

    await waitFor(() => {
      expect(screen.getByText(/Created:/)).toBeInTheDocument();
      expect(screen.getByText(/Modified:/)).toBeInTheDocument();
      expect(screen.getByText(/Size: 1024 bytes/)).toBeInTheDocument();
    });
  });
});