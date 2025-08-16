'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Settings } from 'lucide-react';

interface StorageUsageProps {
  storageUsed: number;
}

const storageBreakdown = [
  { category: 'Models', size: '24.3 GB' },
  { category: 'Datasets', size: '45.8 GB' },
  { category: 'Embeddings', size: '15.2 GB' },
  { category: 'Archives', size: '7.9 GB' },
];

export const StorageUsage: React.FC<StorageUsageProps> = ({ storageUsed }) => {
  return (
    <Card>
      <CardHeader>
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
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <Progress value={storageUsed} className="h-3" />
          <div className="flex justify-between text-sm text-muted-foreground">
            {storageBreakdown.map((item, index) => (
              <span key={index}>{item.category}: {item.size}</span>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};