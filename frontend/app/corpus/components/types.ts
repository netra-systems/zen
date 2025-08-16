// Corpus Management Types
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

export interface PermissionRule {
  userGroup: string;
  role: string;
  accessLevel: string;
}

export interface VersionInfo {
  name: string;
  description: string;
  status: 'active' | 'archived';
  createdDate: string;
  size: string;
  records: string;
}