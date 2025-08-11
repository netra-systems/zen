export interface Corpus {
  name: string;
  description?: string | null;
  id: string;
  status: string;
  created_by_id: string;
  created_at: string;
  updated_at: string;
}

export interface CorpusCreate {
  name: string;
  description?: string | null;
}

export interface CorpusUpdate {
  name: string;
  description?: string | null;
}
