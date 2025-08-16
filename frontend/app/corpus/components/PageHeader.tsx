'use client';

import { Button } from '@/components/ui/button';
import { Upload, Database } from 'lucide-react';
import { useRouter } from 'next/navigation';

export const PageHeader = () => {
  const router = useRouter();

  return (
    <div className="flex justify-between items-center">
      <div>
        <h1 className="text-3xl font-bold">Corpus Management</h1>
        <p className="text-muted-foreground">Organize and manage your data collections</p>
      </div>
      <div className="flex gap-3">
        <Button variant="outline">
          <Upload className="mr-2 h-4 w-4" />
          Import
        </Button>
        <Button onClick={() => router.push('/ingestion')}>
          <Database className="mr-2 h-4 w-4" />
          New Ingestion
        </Button>
      </div>
    </div>
  );
};