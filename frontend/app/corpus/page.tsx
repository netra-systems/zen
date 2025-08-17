'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CorpusHeader } from './components/corpus-header';
import { CorpusStatsGrid } from './components/corpus-stats';
import { CorpusStorage } from './components/corpus-storage';
import { CorpusBrowse } from './components/corpus-browse';
import { CorpusSearch } from './components/corpus-search';
import { CorpusVersions } from './components/corpus-versions';
import { CorpusPermissions } from './components/corpus-permissions';
import { useCorpusState } from './hooks/use-corpus-state';
import { corpusData, statsData, STORAGE_USED_PERCENTAGE } from './data/corpus-data';


const CorpusPage: NextPage = () => {
  const { user, loading } = authService.useAuth();
  const router = useRouter();
  const corpusState = useCorpusState();

  useAuth(loading, user, router);

  if (loading || !user) {
    return <LoadingScreen />;
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <CorpusHeader />
      <CorpusStatsGrid stats={statsData} />
      <CorpusStorage storageUsed={STORAGE_USED_PERCENTAGE} />
      <CorpusTabs corpusState={corpusState} />
    </div>
  );
};

const useAuth = (loading: boolean, user: any, router: any) => {
  useEffect(() => {
    if (!loading && !user) {
      router.push('/login');
    }
  }, [loading, user, router]);
};

const LoadingScreen = () => {
  return (
    <div className="flex items-center justify-center h-screen">
      <p>Loading...</p>
    </div>
  );
};

const CorpusTabs = ({ corpusState }: { corpusState: ReturnType<typeof useCorpusState> }) => {
  return (
    <Tabs value={corpusState.activeTab} onValueChange={corpusState.setActiveTab}>
      <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="browse">Browse</TabsTrigger>
        <TabsTrigger value="search">Search</TabsTrigger>
        <TabsTrigger value="versions">Versions</TabsTrigger>
        <TabsTrigger value="permissions">Permissions</TabsTrigger>
      </TabsList>
      <TabsContent value="browse" className="space-y-4">
        <CorpusBrowse
          corpusData={corpusData}
          searchTerm={corpusState.searchTerm}
          setSearchTerm={corpusState.setSearchTerm}
          filterType={corpusState.filterType}
          setFilterType={corpusState.setFilterType}
          selectedItems={corpusState.selectedItems}
          expandedItems={corpusState.expandedItems}
          onToggleExpand={corpusState.toggleExpand}
          onToggleSelect={corpusState.toggleSelect}
        />
      </TabsContent>
      <TabsContent value="search" className="space-y-4">
        <CorpusSearch />
      </TabsContent>
      <TabsContent value="versions" className="space-y-4">
        <CorpusVersions />
      </TabsContent>
      <TabsContent value="permissions" className="space-y-4">
        <CorpusPermissions />
      </TabsContent>
    </Tabs>
  );
};

export default CorpusPage;