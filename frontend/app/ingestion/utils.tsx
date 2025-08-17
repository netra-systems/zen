// Ingestion Utils Module - Business Value: Reusable utilities reduce code duplication
// Supports Enterprise segment with consistent status indicators and file type recognition

import { 
  Upload, Database, FileJson, Cloud, Server, Webhook, 
  FileText, Code, Image as ImageIcon, Video, Music, Archive,
  CheckCircle, XCircle, Clock, AlertCircle
} from 'lucide-react';
import { IngestionDataSource, IngestionJob } from './types';

export const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'processing':
      return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'queued':
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    default:
      return null;
  }
};

export const getFileIcon = (fileName: string) => {
  const ext = fileName.split('.').pop()?.toLowerCase();
  return getIconByExtension(ext) || getMediaIcon(ext);
};

const getIconByExtension = (ext?: string) => {
  switch (ext) {
    case 'json':
    case 'xml':
      return <FileJson className="h-4 w-4" />;
    case 'txt':
    case 'csv':
      return <FileText className="h-4 w-4" />;
    case 'py':
    case 'js':
    case 'ts':
      return <Code className="h-4 w-4" />;
    default:
      return null;
  }
};

const getMediaIcon = (ext?: string) => {
  switch (ext) {
    case 'jpg':
    case 'png':
    case 'gif':
      return <ImageIcon className="h-4 w-4" />;
    case 'mp4':
    case 'avi':
      return <Video className="h-4 w-4" />;
    case 'mp3':
    case 'wav':
      return <Music className="h-4 w-4" />;
    case 'zip':
    case 'tar':
    case 'gz':
      return <Archive className="h-4 w-4" />;
    default:
      return <FileText className="h-4 w-4" />;
  }
};

export const DATA_SOURCES: IngestionDataSource[] = [
  { id: 'file', label: 'File Upload', icon: <Upload className="h-4 w-4" /> },
  { id: 'database', label: 'Database', icon: <Database className="h-4 w-4" /> },
  { id: 'api', label: 'API Endpoint', icon: <Webhook className="h-4 w-4" /> },
  { id: 'cloud', label: 'Cloud Storage', icon: <Cloud className="h-4 w-4" /> },
  { id: 'streaming', label: 'Real-time Stream', icon: <Server className="h-4 w-4" /> },
];

export const RECENT_INGESTIONS: IngestionJob[] = [
  {
    id: '1',
    name: 'Training Dataset v2.3',
    source: 'S3 Bucket',
    status: 'completed',
    records: '1.2M',
    size: '4.8 GB',
    timestamp: '2 hours ago',
  },
  {
    id: '2',
    name: 'Customer Feedback Logs',
    source: 'PostgreSQL',
    status: 'processing',
    records: '450K',
    size: '892 MB',
    timestamp: '4 hours ago',
    progress: 67,
  },
  {
    id: '3',
    name: 'API Response Cache',
    source: 'Redis Stream',
    status: 'failed',
    records: '89K',
    size: '156 MB',
    timestamp: '6 hours ago',
    error: 'Schema validation failed',
  },
  {
    id: '4',
    name: 'Product Catalog Update',
    source: 'REST API',
    status: 'queued',
    records: '12K',
    size: '45 MB',
    timestamp: '8 hours ago',
  },
];