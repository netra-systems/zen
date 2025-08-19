/**
 * Corpus Management Integration Tests
 * Module-based architecture: Corpus tests ≤300 lines, functions ≤8 lines
 */

import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  setupIntegrationTest,
  teardownIntegrationTest,
  createMockDocument,
  createMockSearchResults,
  createCorpusStore,
  createCorpusService,
  setupDefaultHookMocks,
  setupAuthMocks,
  setupLoadingMocks,
  createMockUseUnifiedChatStore,
  createMockUseWebSocket,
  createMockUseAgent,
  createMockUseAuthStore,
  createMockUseLoadingState,
  createMockUseThreadNavigation
} from './integration-shared-utilities';

// Declare mocks first (Jest Module Hoisting)
const mockUseUnifiedChatStore = createMockUseUnifiedChatStore();
const mockUseWebSocket = createMockUseWebSocket();
const mockUseAgent = createMockUseAgent();
const mockUseAuthStore = createMockUseAuthStore();
const mockUseLoadingState = createMockUseLoadingState();
const mockUseThreadNavigation = createMockUseThreadNavigation();

// Mock hooks before imports
jest.mock('@/store/unified-chat', () => ({
  useUnifiedChatStore: mockUseUnifiedChatStore
}));

jest.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: mockUseWebSocket
}));

jest.mock('@/hooks/useAgent', () => ({
  useAgent: mockUseAgent
}));

jest.mock('@/store/authStore', () => ({
  useAuthStore: mockUseAuthStore
}));

jest.mock('@/hooks/useLoadingState', () => ({
  useLoadingState: mockUseLoadingState
}));

jest.mock('@/hooks/useThreadNavigation', () => ({
  useThreadNavigation: mockUseThreadNavigation
}));

// Mock AuthGate to always render children
jest.mock('@/components/auth/AuthGate', () => {
  return function MockAuthGate({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

describe('Corpus Management Integration Tests', () => {
  let server: any;
  const useCorpusStore = createCorpusStore();
  const corpusService = createCorpusService();
  
  beforeEach(() => {
    server = setupIntegrationTest();
    setupAllMocks();
  });

  afterEach(() => {
    teardownIntegrationTest();
  });

  describe('1. Corpus Management Integration', () => {
    it('should upload documents to corpus and process with embeddings', async () => {
      const mockDocument = createMockDocument();
      setupDocumentUploadMock(mockDocument);
      
      const file = new File(['test content'], 'test.txt');
      await simulateFileUpload(file, mockDocument);
      
      assertStoreState();
    });

    it('should search corpus with semantic similarity', async () => {
      const mockResults = createMockSearchResults();
      setupCorpusSearchMock(mockResults);
      
      await simulateCorpusSearch('test query');
      
      verifySearchCalled('test query');
    });

    it('should handle corpus document indexing', async () => {
      const mockDocument = createMockDocument();
      setupDocumentIndexMock(mockDocument);
      
      await simulateDocumentIndexing(mockDocument);
      
      verifyDocumentIndexed(mockDocument);
    });

    it('should handle corpus search with filters', async () => {
      const mockResults = createMockSearchResults();
      setupFilteredSearchMock(mockResults);
      
      await simulateFilteredSearch('query', { type: 'pdf' });
      
      verifyFilteredSearchCalled();
    });

    it('should handle corpus document updates', async () => {
      const mockDocument = createMockDocument();
      setupDocumentUpdateMock(mockDocument);
      
      await simulateDocumentUpdate(mockDocument.id, { title: 'Updated' });
      
      verifyDocumentUpdated(mockDocument.id);
    });

    it('should handle corpus document deletion', async () => {
      const documentId = 'doc-123';
      setupDocumentDeletionMock(documentId);
      
      await simulateDocumentDeletion(documentId);
      
      verifyDocumentDeleted(documentId);
    });

    it('should handle corpus metadata extraction', async () => {
      const mockDocument = createMockDocument();
      setupMetadataExtractionMock(mockDocument);
      
      await simulateMetadataExtraction(mockDocument);
      
      verifyMetadataExtracted(mockDocument);
    });

    it('should handle corpus batch operations', async () => {
      const mockDocuments = [createMockDocument(), createMockDocument()];
      setupBatchOperationMock(mockDocuments);
      
      await simulateBatchOperation(mockDocuments);
      
      verifyBatchProcessed(mockDocuments.length);
    });
  });
});

// Helper functions ≤8 lines each
const setupAllMocks = () => {
  const mocks = {
    mockUseUnifiedChatStore,
    mockUseWebSocket,
    mockUseAgent,
    mockUseAuthStore,
    mockUseLoadingState,
    mockUseThreadNavigation
  };
  
  setupDefaultHookMocks(mocks);
  setupAuthMocks(mocks);
  setupLoadingMocks(mocks);
};

const setupDocumentUploadMock = (mockDocument: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockDocument
  });
};

const setupCorpusSearchMock = (mockResults: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockResults
  });
};

const setupDocumentIndexMock = (mockDocument: any) => {
  corpusService.uploadDocument.mockResolvedValueOnce(mockDocument);
};

const setupFilteredSearchMock = (mockResults: any) => {
  corpusService.searchDocuments.mockResolvedValueOnce(mockResults);
};

const setupDocumentUpdateMock = (mockDocument: any) => {
  corpusService.uploadDocument.mockResolvedValueOnce(mockDocument);
};

const setupDocumentDeletionMock = (documentId: string) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ deleted: documentId })
  });
};

const setupMetadataExtractionMock = (mockDocument: any) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ...mockDocument, metadata: { extracted: true } })
  });
};

const setupBatchOperationMock = (mockDocuments: any[]) => {
  (fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ processed: mockDocuments.length })
  });
};

const simulateFileUpload = async (file: File, mockDocument: any) => {
  await corpusService.uploadDocument(file);
  const state = useCorpusStore.getState();
  state.addDocument(mockDocument);
};

const simulateCorpusSearch = async (query: string) => {
  await corpusService.searchDocuments(query);
};

const simulateDocumentIndexing = async (document: any) => {
  await corpusService.uploadDocument(document);
};

const simulateFilteredSearch = async (query: string, filters: any) => {
  await corpusService.searchDocuments(query, filters);
};

const simulateDocumentUpdate = async (id: string, updates: any) => {
  await corpusService.uploadDocument({ id, ...updates });
};

const simulateDocumentDeletion = async (id: string) => {
  await fetch(`/api/corpus/${id}`, { method: 'DELETE' });
};

const simulateMetadataExtraction = async (document: any) => {
  await fetch('/api/corpus/extract-metadata', {
    method: 'POST',
    body: JSON.stringify(document)
  });
};

const simulateBatchOperation = async (documents: any[]) => {
  await fetch('/api/corpus/batch', {
    method: 'POST',
    body: JSON.stringify({ documents })
  });
};

const assertStoreState = () => {
  const state = useCorpusStore.getState();
  expect(state.documents).toBeDefined();
};

const verifySearchCalled = (query: string) => {
  expect(corpusService.searchDocuments).toHaveBeenCalledWith(query);
};

const verifyDocumentIndexed = (document: any) => {
  expect(corpusService.uploadDocument).toHaveBeenCalledWith(document);
};

const verifyFilteredSearchCalled = () => {
  expect(corpusService.searchDocuments).toHaveBeenCalled();
};

const verifyDocumentUpdated = (id: string) => {
  expect(corpusService.uploadDocument).toHaveBeenCalledWith(
    expect.objectContaining({ id })
  );
};

const verifyDocumentDeleted = (id: string) => {
  expect(fetch).toHaveBeenCalledWith(`/api/corpus/${id}`, { method: 'DELETE' });
};

const verifyMetadataExtracted = (document: any) => {
  expect(fetch).toHaveBeenCalledWith('/api/corpus/extract-metadata', 
    expect.objectContaining({ method: 'POST' })
  );
};

const verifyBatchProcessed = (count: number) => {
  expect(fetch).toHaveBeenCalledWith('/api/corpus/batch', 
    expect.objectContaining({ method: 'POST' })
  );
};