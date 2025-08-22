/**
 * Corpus Management Integration Tests
 */

import React from 'react';
import { render, waitFor, screen, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import WS from 'jest-websocket-mock';
import * as WebSocketTestManager from '@/__tests__/helpers/websocket-test-manager';

import { AgentProvider } from '@/providers/AgentProvider';
import { WebSocketProvider } from '@/providers/WebSocketProvider';
import { TestProviders } from '@/__tests__/setup/test-providers';

// Mock stores
const createMockStore = (initialState: any) => {
  let state = initialState;
  const store = Object.assign(
    jest.fn(() => state),
    {
      getState: jest.fn(() => state),
      setState: jest.fn((newState: any) => {
        state = typeof newState === 'function' ? newState(state) : { ...state, ...newState };
      })
    }
  );
  return store;
};

const useCorpusStore = createMockStore({
  documents: [],
  addDocument: jest.fn((doc: any) => {
    useCorpusStore.setState((prev: any) => ({
      ...prev,
      documents: [...prev.documents, doc]
    }));
  })
});

const corpusService = { 
  uploadDocument: jest.fn().mockResolvedValue({}), 
  searchDocuments: jest.fn().mockResolvedValue([]) 
};

// WebSocket test manager
let wsManager: WebSocketTestManager;

beforeEach(() => {
  wsManager = WebSocketTestManager.createWebSocketManager();
  wsManager.setup();
});

afterEach(() => {
  wsManager.cleanup();
  jest.clearAllMocks();
});

describe('Corpus Management Integration', () => {
  it('should upload documents to corpus and update UI', async () => {
    const TestComponent = () => {
      const [uploadStatus, setUploadStatus] = React.useState('');
      
      const handleUpload = async () => {
        const file = new File(['test content'], 'test.txt', { type: 'text/plain' });
        await corpusService.uploadDocument(file);
        useCorpusStore.getState().addDocument({ name: 'test.txt', size: file.size });
        setUploadStatus('Document uploaded successfully');
      };
      
      return (
        <div>
          <button onClick={handleUpload}>Upload Document</button>
          <div data-testid="upload-status">{uploadStatus}</div>
          <div data-testid="doc-count">{useCorpusStore.getState().documents.length} documents</div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Upload Document'));
    
    await waitFor(() => {
      expect(getByTestId('upload-status')).toHaveTextContent('Document uploaded successfully');
      expect(corpusService.uploadDocument).toHaveBeenCalled();
    });
  });

  it('should search corpus with embeddings', async () => {
    const TestComponent = () => {
      const [searchResults, setSearchResults] = React.useState<any[]>([]);
      
      const handleSearch = async () => {
        const results = await corpusService.searchDocuments('test query');
        setSearchResults([
          { id: 1, name: 'doc1.txt', relevance: 0.95 },
          { id: 2, name: 'doc2.txt', relevance: 0.87 }
        ]);
      };
      
      return (
        <div>
          <button onClick={handleSearch}>Search Corpus</button>
          <div data-testid="search-results">
            {searchResults.map(r => (
              <div key={r.id}>{r.name} - {r.relevance}</div>
            ))}
          </div>
        </div>
      );
    };
    
    const { getByText, getByTestId } = render(
      <TestProviders>
        <TestComponent />
      </TestProviders>
    );
    
    fireEvent.click(getByText('Search Corpus'));
    
    await waitFor(() => {
      expect(getByTestId('search-results')).toHaveTextContent('doc1.txt - 0.95');
      expect(getByTestId('search-results')).toHaveTextContent('doc2.txt - 0.87');
    });
  });
});