import { CorpusItem, CorpusStats } from '../types/corpus';
import { FolderOpen, Database, Activity, File } from 'lucide-react';

export const corpusData: CorpusItem[] = [
  {
    id: '1',
    name: 'Production Models',
    type: 'collection',
    size: '12.4 GB',
    records: '45.2K',
    lastModified: '2 hours ago',
    status: 'active',
    owner: 'System',
    accessLevel: 'restricted',
    version: 'v3.2',
    children: [
      {
        id: '11',
        name: 'GPT-4 Fine-tuned',
        type: 'model',
        size: '4.8 GB',
        records: '12K',
        lastModified: '1 day ago',
        status: 'active',
        owner: 'ML Team',
        accessLevel: 'private',
        version: 'v2.1',
      },
      {
        id: '12',
        name: 'Claude-3 Optimized',
        type: 'model',
        size: '3.2 GB',
        records: '8.5K',
        lastModified: '3 days ago',
        status: 'active',
        owner: 'ML Team',
        accessLevel: 'private',
        version: 'v1.8',
      },
    ],
  },
  {
    id: '2',
    name: 'Training Datasets',
    type: 'collection',
    size: '28.7 GB',
    records: '2.1M',
    lastModified: '5 hours ago',
    status: 'active',
    owner: 'Data Team',
    accessLevel: 'public',
    version: 'v4.0',
    children: [
      {
        id: '21',
        name: 'Customer Interactions',
        type: 'dataset',
        size: '8.2 GB',
        records: '890K',
        lastModified: '6 hours ago',
        status: 'processing',
        owner: 'Analytics',
        accessLevel: 'restricted',
        version: 'v2.3',
      },
      {
        id: '22',
        name: 'Product Reviews',
        type: 'dataset',
        size: '5.6 GB',
        records: '450K',
        lastModified: '1 week ago',
        status: 'active',
        owner: 'Product Team',
        accessLevel: 'public',
        version: 'v1.5',
      },
      {
        id: '23',
        name: 'Support Tickets',
        type: 'dataset',
        size: '3.8 GB',
        records: '320K',
        lastModified: '2 days ago',
        status: 'active',
        owner: 'Support Team',
        accessLevel: 'restricted',
        version: 'v3.1',
      },
    ],
  },
  {
    id: '3',
    name: 'Vector Embeddings',
    type: 'embedding',
    size: '6.9 GB',
    records: '780K',
    lastModified: '12 hours ago',
    status: 'active',
    owner: 'ML Team',
    accessLevel: 'private',
    version: 'v2.0',
  },
  {
    id: '4',
    name: 'Archived Data',
    type: 'collection',
    size: '45.2 GB',
    records: '5.6M',
    lastModified: '1 month ago',
    status: 'archived',
    owner: 'Admin',
    accessLevel: 'private',
    version: 'v1.0',
  },
];

export const statsData: CorpusStats[] = [
  { 
    label: 'Total Collections', 
    value: '24', 
    icon: <FolderOpen className="h-4 w-4" /> 
  },
  { 
    label: 'Active Datasets', 
    value: '156', 
    icon: <Database className="h-4 w-4" /> 
  },
  { 
    label: 'Models', 
    value: '12', 
    icon: <Activity className="h-4 w-4" /> 
  },
  { 
    label: 'Total Records', 
    value: '8.4M', 
    icon: <File className="h-4 w-4" /> 
  },
];

export const STORAGE_USED_PERCENTAGE = 68;