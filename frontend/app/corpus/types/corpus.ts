export interface CorpusItem {
  id: string;
  name: string;
  type: 'collection' | 'dataset' | 'model' | 'embedding';
  size: string;
  records: string;
  lastModified: string;
  status: 'active' | 'processing' | 'archived';
  owner: string;
  accessLevel: 'public' | 'private' | 'restricted';
  version: string;
  children?: CorpusItem[];
}

export interface CorpusStats {
  label: string;
  value: string;
  icon: React.ReactNode;
}

export type TabType = 'browse' | 'search' | 'versions' | 'permissions';
export type FilterType = 'all' | 'collection' | 'dataset' | 'model' | 'embedding';