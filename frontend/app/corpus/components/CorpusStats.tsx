'use client';

import { Card, CardContent } from '@/components/ui/card';
import { FolderOpen, Database, Activity, File } from 'lucide-react';
import type { CorpusStats } from './types';

const stats: CorpusStats[] = [
  { label: 'Total Collections', value: '24', icon: <FolderOpen className="h-4 w-4" /> },
  { label: 'Active Datasets', value: '156', icon: <Database className="h-4 w-4" /> },
  { label: 'Models', value: '12', icon: <Activity className="h-4 w-4" /> },
  { label: 'Total Records', value: '8.4M', icon: <File className="h-4 w-4" /> },
];

export const CorpusStats = () => {
  return (
    <div className="grid grid-cols-4 gap-4">
      {stats.map((stat, index) => (
        <Card key={index}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="text-2xl font-bold">{stat.value}</p>
              </div>
              {stat.icon}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};