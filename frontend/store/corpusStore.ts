import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { Corpus, CorpusCreate, CorpusUpdate } from '@/types/Corpus';

interface CorpusDocument {
  id: string;
  name: string;
  corpus_id: string;
  content?: string;
  created_at: string;
  updated_at: string;
}

interface CorpusState {
  corpora: Corpus[];
  documents: CorpusDocument[];
  currentCorpus: Corpus | null;
  loading: boolean;
  error: string | null;
  
  // Corpus actions
  setCorpora: (corpora: Corpus[]) => void;
  addCorpus: (corpus: Corpus) => void;
  updateCorpus: (id: string, update: CorpusUpdate) => void;
  removeCorpus: (id: string) => void;
  setCurrentCorpus: (corpus: Corpus | null) => void;
  
  // Document actions
  setDocuments: (documents: CorpusDocument[]) => void;
  addDocument: (document: CorpusDocument) => void;
  updateDocument: (id: string, update: Partial<CorpusDocument>) => void;
  removeDocument: (id: string) => void;
  
  // UI state actions
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  
  // Helper methods
  getDocumentsByCorpus: (corpusId: string) => CorpusDocument[];
  getCorpusById: (id: string) => Corpus | undefined;
}

export const useCorpusStore = create<CorpusState>()(
  immer((set, get) => ({
    corpora: [],
    documents: [],
    currentCorpus: null,
    loading: false,
    error: null,

    setCorpora: (corpora) =>
      set((state) => {
        state.corpora = corpora;
        state.error = null;
      }),

    addCorpus: (corpus) =>
      set((state) => {
        state.corpora.push(corpus);
        state.error = null;
      }),

    updateCorpus: (id, update) =>
      set((state) => {
        const index = state.corpora.findIndex(c => c.id === id);
        if (index !== -1) {
          state.corpora[index] = { ...state.corpora[index], ...update };
        }
      }),

    removeCorpus: (id) =>
      set((state) => {
        state.corpora = state.corpora.filter(c => c.id !== id);
        if (state.currentCorpus?.id === id) {
          state.currentCorpus = null;
        }
      }),

    setCurrentCorpus: (corpus) =>
      set((state) => {
        state.currentCorpus = corpus;
        state.error = null;
      }),

    setDocuments: (documents) =>
      set((state) => {
        state.documents = documents;
        state.error = null;
      }),

    addDocument: (document) =>
      set((state) => {
        state.documents.push(document);
        state.error = null;
      }),

    updateDocument: (id, update) =>
      set((state) => {
        const index = state.documents.findIndex(d => d.id === id);
        if (index !== -1) {
          state.documents[index] = { ...state.documents[index], ...update };
        }
      }),

    removeDocument: (id) =>
      set((state) => {
        state.documents = state.documents.filter(d => d.id !== id);
      }),

    setLoading: (loading) =>
      set((state) => {
        state.loading = loading;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),

    reset: () =>
      set((state) => {
        state.corpora = [];
        state.documents = [];
        state.currentCorpus = null;
        state.loading = false;
        state.error = null;
      }),

    getDocumentsByCorpus: (corpusId) => {
      const state = get();
      return state.documents.filter(doc => doc.corpus_id === corpusId);
    },

    getCorpusById: (id) => {
      const state = get();
      return state.corpora.find(corpus => corpus.id === id);
    },
  }))
);