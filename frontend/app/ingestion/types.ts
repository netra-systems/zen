// Ingestion Types Module - Business Value: Type safety for data ingestion workflows
// Supports all customer segments by ensuring reliable data processing

export interface IngestionConfig {
  dataSource: string;
  format: string;
  chunkSize: string;
  enableValidation: boolean;
  enableDeduplication: boolean;
  enableCompression: boolean;
  processingMode: string;
}

export interface IngestionJob {
  id: string;
  name: string;
  source: string;
  status: 'completed' | 'processing' | 'failed' | 'queued';
  records: string;
  size: string;
  timestamp: string;
  progress?: number;
  error?: string;
}

export interface IngestionDataSource {
  id: string;
  label: string;
  icon: React.ReactNode;
}