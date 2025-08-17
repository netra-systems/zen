import { 
  FolderOpen, Database, Activity, Hash, File,
  Unlock, Lock, Shield
} from 'lucide-react';
import { CorpusItem, FilterType } from '../types/corpus';

export const getTypeIcon = (type: string) => {
  switch (type) {
    case 'collection':
      return <FolderOpen className="h-4 w-4 text-blue-500" />;
    case 'dataset':
      return <Database className="h-4 w-4 text-green-500" />;
    case 'model':
      return <Activity className="h-4 w-4 text-purple-500" />;
    case 'embedding':
      return <Hash className="h-4 w-4 text-orange-500" />;
    default:
      return <File className="h-4 w-4 text-gray-500" />;
  }
};

export const getAccessIcon = (level: string) => {
  switch (level) {
    case 'public':
      return <Unlock className="h-3 w-3 text-green-500" />;
    case 'private':
      return <Lock className="h-3 w-3 text-red-500" />;
    case 'restricted':
      return <Shield className="h-3 w-3 text-yellow-500" />;
    default:
      return null;
  }
};

export const filterCorpusData = (
  data: CorpusItem[], 
  filterType: FilterType, 
  searchTerm: string
): CorpusItem[] => {
  return data.filter(item => 
    (filterType === 'all' || item.type === filterType) &&
    (searchTerm === '' || item.name.toLowerCase().includes(searchTerm.toLowerCase()))
  );
};

export const getStatusBadgeVariant = (status: string) => {
  switch (status) {
    case 'active':
      return 'default';
    case 'processing':
      return 'secondary';
    default:
      return 'outline';
  }
};