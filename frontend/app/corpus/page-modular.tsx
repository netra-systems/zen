'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  PageHeader,
  CorpusStats,
  StorageUsage,
  BrowseTab,
  SearchTab,
  VersionsTab,
  PermissionsTab,
  type CorpusItemType
} from './components';

// Sample corpus data
const corpusData: CorpusItemType[] = [
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
];

const CorpusPageModular: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('browse');
  const [storageUsed] = useState(68);

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <PageHeader />
      <CorpusStats />
      <StorageUsage storageUsed={storageUsed} />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="browse">Browse</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
        </TabsList>

        <TabsContent value="browse" className="space-y-4">
          <BrowseTab corpusData={corpusData} />
        </TabsContent>

        <TabsContent value="search" className="space-y-4">
          <SearchTab />
        </TabsContent>

        <TabsContent value="versions" className="space-y-4">
          <VersionsTab />
        </TabsContent>

        <TabsContent value="permissions" className="space-y-4">
          <PermissionsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default CorpusPageModular;