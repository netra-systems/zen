import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Settings } from 'lucide-react';

interface CorpusStorageProps {
  storageUsed: number;
}

export const CorpusStorage = ({ storageUsed }: CorpusStorageProps) => {
  return (
    <Card>
      <CardHeader>
        <StorageHeader />
      </CardHeader>
      <CardContent>
        <StorageContent storageUsed={storageUsed} />
      </CardContent>
    </Card>
  );
};

const StorageHeader = () => {
  return (
    <div className="flex justify-between items-center">
      <div>
        <CardTitle>Storage Usage</CardTitle>
        <CardDescription>93.2 GB of 150 GB used</CardDescription>
      </div>
      <Button variant="outline" size="sm">
        <Settings className="mr-2 h-4 w-4" />
        Manage Storage
      </Button>
    </div>
  );
};

const StorageContent = ({ storageUsed }: { storageUsed: number }) => {
  return (
    <div className="space-y-2">
      <Progress value={storageUsed} className="h-3" />
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>Models: 24.3 GB</span>
        <span>Datasets: 45.8 GB</span>
        <span>Embeddings: 15.2 GB</span>
        <span>Archives: 7.9 GB</span>
      </div>
    </div>
  );
};