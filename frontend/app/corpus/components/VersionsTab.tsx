'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Calendar, HardDrive, BarChart3, RefreshCw, Eye } from 'lucide-react';
import type { VersionInfo } from './types';

const versionData: VersionInfo[] = [
  {
    name: 'Production Models v3.2',
    description: 'Current version',
    status: 'active',
    createdDate: 'March 15, 2024',
    size: '12.4 GB',
    records: '45,231 records',
  },
  {
    name: 'Production Models v3.1',
    description: 'Previous version',
    status: 'archived',
    createdDate: 'February 28, 2024',
    size: '11.8 GB',
    records: '42,156 records',
  },
];

const VersionMetric: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string;
}> = ({ icon, label, value }) => (
  <div className="flex items-center gap-2 text-sm">
    {icon}
    <span>{label}: {value}</span>
  </div>
);

const VersionCard: React.FC<{ version: VersionInfo }> = ({ version }) => {
  const isActive = version.status === 'active';
  
  return (
    <div className={`border rounded-lg p-4 ${!isActive ? 'opacity-75' : ''}`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold">{version.name}</h3>
          <p className="text-sm text-muted-foreground">{version.description}</p>
        </div>
        <Badge variant={isActive ? 'default' : 'secondary'}>
          {isActive ? 'Active' : 'Archived'}
        </Badge>
      </div>
      <div className="space-y-2">
        <VersionMetric
          icon={<Calendar className="h-4 w-4 text-muted-foreground" />}
          label="Created"
          value={version.createdDate}
        />
        <VersionMetric
          icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
          label="Size"
          value={version.size}
        />
        <VersionMetric
          icon={<BarChart3 className="h-4 w-4 text-muted-foreground" />}
          label="Records"
          value={version.records}
        />
      </div>
      {!isActive && (
        <div className="flex gap-2 mt-4">
          <Button size="sm" variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Restore
          </Button>
          <Button size="sm" variant="outline">
            <Eye className="mr-2 h-4 w-4" />
            Compare
          </Button>
        </div>
      )}
    </div>
  );
};

export const VersionsTab = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Version Control</CardTitle>
        <CardDescription>Track and manage different versions of your data</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {versionData.map((version, index) => (
            <VersionCard key={index} version={version} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};