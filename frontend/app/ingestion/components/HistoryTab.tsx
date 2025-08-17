// History Tab Component - Business Value: Ingestion transparency builds customer trust
// Supports all segments with audit trail and troubleshooting capabilities

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { getStatusIcon, RECENT_INGESTIONS } from '../utils';
import { IngestionJob } from '../types';

export const HistoryTab = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Ingestion History</CardTitle>
        <CardDescription>View past ingestion jobs and their results</CardDescription>
      </CardHeader>
      <CardContent>
        <HistoryJobsList jobs={RECENT_INGESTIONS} />
      </CardContent>
    </Card>
  );
};

const HistoryJobsList = ({ jobs }: { jobs: IngestionJob[] }) => {
  return (
    <div className="space-y-4">
      {jobs.map((job) => (
        <HistoryJobItem key={job.id} job={job} />
      ))}
    </div>
  );
};

const HistoryJobItem = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex justify-between items-start">
        <JobDetails job={job} />
        <JobActions job={job} />
      </div>
    </div>
  );
};

const JobDetails = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="space-y-1">
      <JobHeader job={job} />
      <JobMetrics job={job} />
      <JobError job={job} />
    </div>
  );
};

const JobHeader = ({ job }: { job: IngestionJob }) => {
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

const JobError = ({ job }: { job: IngestionJob }) => {
  if (!job.error) return null;

  return (
    <Alert className="mt-2">
      <AlertCircle className="h-4 w-4" />
      <AlertDescription>{job.error}</AlertDescription>
    </Alert>
  );
};

const JobActions = ({ job }: { job: IngestionJob }) => {
  return (
    <div className="flex gap-2">
      <ViewDetailsButton />
      <RetryButton job={job} />
    </div>
  );
};

const ViewDetailsButton = () => {
  return (
    <Button size="sm" variant="outline">
      View Details
    </Button>
  );
};

const RetryButton = ({ job }: { job: IngestionJob }) => {
  if (job.status !== 'failed') return null;

  return (
    <Button size="sm" variant="outline">
      <RefreshCw className="h-3 w-3 mr-1" />
      Retry
    </Button>
  );
};