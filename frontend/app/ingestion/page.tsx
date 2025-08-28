// Main Ingestion Page - Business Value: Central hub for all data ingestion workflows
// Orchestrates modular components to support all customer segments efficiently

'use client';

import { NextPage } from 'next';
import { authService } from '@/auth';
import { useRouter } from 'next/navigation';
import { AuthGuard } from '@/components/AuthGuard';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Database } from 'lucide-react';
import { IngestionConfig } from './types';
import { DataSourceConfig } from './components/DataSourceConfig';
import { FileUploadSection } from './components/FileUploadSection';
import { ActiveJobsTab } from './components/ActiveJobsTab';
import { HistoryTab } from './components/HistoryTab';
import { SettingsTab } from './components/SettingsTab';

const IngestionPage: NextPage = () => {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [ingestionConfig, setIngestionConfig] = useState<IngestionConfig>({
    dataSource: 'file',
    format: 'json',
    chunkSize: '1024',
    enableValidation: true,
    enableDeduplication: true,
    enableCompression: false,
    processingMode: 'batch',
  });

  const handleStartIngestion = () => {
    setIsProcessing(true);
    setUploadProgress(0);
    simulateProgress();
  };

  const simulateProgress = () => {
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsProcessing(false);
          return 100;
        }
        return prev + 10;
      });
    }, 500);
  };

  return (
    <AuthGuard>
      <div className="container mx-auto p-6 space-y-6">
        <PageHeader onViewCorpus={() => router.push('/corpus')} />
        <MainTabs 
          activeTab={activeTab}
          onTabChange={setActiveTab}
          config={ingestionConfig}
          onConfigChange={setIngestionConfig}
          isProcessing={isProcessing}
          uploadProgress={uploadProgress}
          onStartIngestion={handleStartIngestion}
        />
      </div>
    </AuthGuard>
  );
};

const LoadingScreen = () => {
  return (
    <div className="flex items-center justify-center h-screen">
      <p>Loading...</p>
    </div>
  );
};

const PageHeader = ({ onViewCorpus }: { onViewCorpus: () => void }) => {
  return (
    <div className="flex justify-between items-center">
      <HeaderContent />
      <ViewCorpusButton onViewCorpus={onViewCorpus} />
    </div>
  );
};

const HeaderContent = () => {
  return (
    <div>
      <h1 className="text-3xl font-bold">Data Ingestion</h1>
      <p className="text-muted-foreground">Import and process data from multiple sources</p>
    </div>
  );
};

const ViewCorpusButton = ({ onViewCorpus }: { onViewCorpus: () => void }) => {
  return (
    <Button onClick={onViewCorpus}>
      View Corpus
      <Database className="ml-2 h-4 w-4" />
    </Button>
  );
};

interface MainTabsProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  config: IngestionConfig;
  onConfigChange: (config: IngestionConfig) => void;
  isProcessing: boolean;
  uploadProgress: number;
  onStartIngestion: () => void;
}

const MainTabs = ({ 
  activeTab, 
  onTabChange, 
  config, 
  onConfigChange, 
  isProcessing, 
  uploadProgress, 
  onStartIngestion 
}: MainTabsProps) => {
  return (
    <Tabs value={activeTab} onValueChange={onTabChange}>
      <TabsNavigation />
      <TabsContent value="upload" className="space-y-6">
        <NewIngestionTab 
          config={config}
          onConfigChange={onConfigChange}
          isProcessing={isProcessing}
          uploadProgress={uploadProgress}
          onStartIngestion={onStartIngestion}
        />
      </TabsContent>
      <TabsContent value="active" className="space-y-4">
        <ActiveJobsTab />
      </TabsContent>
      <TabsContent value="history" className="space-y-4">
        <HistoryTab />
      </TabsContent>
      <TabsContent value="settings" className="space-y-4">
        <SettingsTab />
      </TabsContent>
    </Tabs>
  );
};

const TabsNavigation = () => {
  return (
    <TabsList className="grid w-full grid-cols-4">
      <TabsTrigger value="upload">New Ingestion</TabsTrigger>
      <TabsTrigger value="active">Active Jobs</TabsTrigger>
      <TabsTrigger value="history">History</TabsTrigger>
      <TabsTrigger value="settings">Settings</TabsTrigger>
    </TabsList>
  );
};

interface NewIngestionTabProps {
  config: IngestionConfig;
  onConfigChange: (config: IngestionConfig) => void;
  isProcessing: boolean;
  uploadProgress: number;
  onStartIngestion: () => void;
}

const NewIngestionTab = ({ 
  config, 
  onConfigChange, 
  isProcessing, 
  uploadProgress, 
  onStartIngestion 
}: NewIngestionTabProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Configure Data Source</CardTitle>
        <CardDescription>Select how you want to ingest data into the system</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <DataSourceConfig config={config} onConfigChange={onConfigChange} />
        <FileUploadSection 
          config={config}
          isProcessing={isProcessing}
          uploadProgress={uploadProgress}
          onStartIngestion={onStartIngestion}
        />
      </CardContent>
    </Card>
  );
};

export default IngestionPage;