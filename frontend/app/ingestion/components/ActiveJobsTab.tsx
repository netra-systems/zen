// Active Jobs Tab Component - Business Value: Real-time job monitoring increases customer confidence
// Supports Growth & Enterprise segments with professional operational visibility

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Pause, XCircle } from 'lucide-react';
import { getStatusIcon, RECENT_INGESTIONS } from '../utils';
import { IngestionJob } from '../types';

export const ActiveJobsTab = () => {
  const activeJobs = RECENT_INGESTIONS.filter((job) => job.status === 'processing');

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active Ingestion Jobs</CardTitle>
        <CardDescription>Monitor ongoing data ingestion processes</CardDescription>
      </CardHeader>
      <CardContent>
        <ActiveJobsList jobs={activeJobs} />
      </CardContent>
    </Card>
  );
};

const ActiveJobsList = ({ jobs }: { jobs: IngestionJob[] }) => {
  return (
    <div className="space-y-4">
      {jobs.map((job) => (
        <ActiveJobItem key={job.id} job={job} />
      ))}
    </div>
  );
};

const ActiveJobItem = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="border rounded-lg p-4 space-y-3">
      <JobHeader job={job} />
      <JobProgress job={job} />
    </div>
  );
};

const JobHeader = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="flex justify-between items-start">
      <JobInfo job={job} />
      <JobActions />
    </div>
  );
};

const JobInfo = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="space-y-1">
      <JobTitle job={job} />
      <JobMetrics job={job} />
    </div>
  );
};

const JobTitle = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="flex items-center gap-2">
      {getStatusIcon(job.status)}
      <p className="font-medium">{job.name}</p>
      <Badge variant="secondary">{job.source}</Badge>
    </div>
  );
};

const JobMetrics = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="flex gap-4 text-sm text-muted-foreground">
      <span>{job.records} records</span>
      <span>{job.size}</span>
      <span>{job.timestamp}</span>
    </div>
  );
};

const JobActions = () => {
  return (
    <div className="flex gap-2">
      <PauseButton />
      <CancelButton />
    </div>
  );
};

const PauseButton = () => {
  return (
    <Button size="sm" variant="outline">
      <Pause className="h-3 w-3" />
    </Button>
  );
};

const CancelButton = () => {
  return (
    <Button size="sm" variant="outline">
      <XCircle className="h-3 w-3" />
    </Button>
  );
};

const JobProgress = ({ job }: { job: IngestionJob }) => {
  if (!job.progress) return null;

  return (
    <div className="space-y-1">
      <ProgressHeader progress={job.progress} />
      <Progress value={job.progress} className="h-2" />
    </div>
  );
};

const ProgressHeader = ({ progress }: { progress: number }) => {
  return (
    <div className="flex justify-between text-sm">
      <span>Progress</span>
      <span>{progress}%</span>
    </div>
  );
};