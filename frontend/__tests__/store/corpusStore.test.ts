/**
 * CorpusStore Tests - Verify store functionality
 * Tests the corpusStore implementation
 */

import { useCorpusStore } from '@/store/corpusStore';

describe('CorpusStore', () => {
  beforeEach(() => {
    useCorpusStore.getState().reset();
  });

  it('should add document correctly', () => {
    const mockDocument = {
      id: 'doc-1',
      name: 'Test Document',
      corpus_id: 'corpus-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    useCorpusStore.getState().addDocument(mockDocument);
    const { documents } = useCorpusStore.getState();
    expect(documents).toHaveLength(1);
    expect(documents[0]).toEqual(mockDocument);
  });

  it('should add corpus correctly', () => {
    const mockCorpus = {
      id: 'corpus-1',
      name: 'Test Corpus',
      description: 'Test Description',
      status: 'active',
      created_by_id: 'user-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    useCorpusStore.getState().addCorpus(mockCorpus);
    const { corpora } = useCorpusStore.getState();
    expect(corpora).toHaveLength(1);
    expect(corpora[0]).toEqual(mockCorpus);
  });

  it('should get documents by corpus ID', () => {
    const doc1 = {
      id: 'doc-1',
      name: 'Doc 1',
      corpus_id: 'corpus-1',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };
    const doc2 = {
      id: 'doc-2', 
      name: 'Doc 2',
      corpus_id: 'corpus-2',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    };

    useCorpusStore.getState().addDocument(doc1);
    useCorpusStore.getState().addDocument(doc2);
    
    const corpus1Docs = useCorpusStore.getState().getDocumentsByCorpus('corpus-1');
    expect(corpus1Docs).toHaveLength(1);
    expect(corpus1Docs[0].id).toBe('doc-1');
  });
});