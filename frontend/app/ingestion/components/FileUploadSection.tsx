// File Upload Section Component - Business Value: Simplified file ingestion for all customer segments
// Reduces customer's data preparation time and costs

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Clock, Play, Pause } from 'lucide-react';
import { getFileIcon } from '../utils';
import { IngestionConfig } from '../types';

interface FileUploadSectionProps {
  config: IngestionConfig;
  isProcessing: boolean;
  uploadProgress: number;
  onStartIngestion: () => void;
}

export const FileUploadSection = ({ 
  config, 
  isProcessing, 
  uploadProgress, 
  onStartIngestion 
}: FileUploadSectionProps) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  return (
    <div className="space-y-4">
      {config.dataSource === 'file' && (
        <FileSelectionSection 
          selectedFiles={selectedFiles} 
          onFileChange={setSelectedFiles} 
        />
      )}
      <ProgressSection isProcessing={isProcessing} uploadProgress={uploadProgress} />
      <ActionButtons 
        isProcessing={isProcessing} 
        onStartIngestion={onStartIngestion} 
      />
    </div>
  );
};

interface FileSelectionProps {
  selectedFiles: File[];
  onFileChange: (files: File[]) => void;
}

const FileSelectionSection = ({ selectedFiles, onFileChange }: FileSelectionProps) => {
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    onFileChange(files);
  };

  return (
    <div className="space-y-4">
      <FileInputField onFileChange={handleFileUpload} />
      <SelectedFilesList selectedFiles={selectedFiles} />
    </div>
  );
};

const FileInputField = ({ onFileChange }: { onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void }) => {
  return (
    <div>
      <Label htmlFor="file-upload">Select Files</Label>
      <Input
        id="file-upload"
        type="file"
        multiple
        onChange={onFileChange}
        className="mt-2"
      />
    </div>
  );
};

const SelectedFilesList = ({ selectedFiles }: { selectedFiles: File[] }) => {
  if (selectedFiles.length === 0) return null;

  return (
    <div className="border rounded-lg p-4 space-y-2">
      <p className="text-sm font-medium">Selected Files:</p>
      {selectedFiles.map((file, index) => (
        <FileListItem key={index} file={file} />
      ))}
    </div>
  );
};

const FileListItem = ({ file }: { file: File }) => {
  const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
  
  return (
    <div className="flex items-center gap-2 text-sm">
      {getFileIcon(file.name)}
      <span>{file.name}</span>
      <Badge variant="secondary">{fileSizeMB} MB</Badge>
    </div>
  );
};

interface ProgressSectionProps {
  isProcessing: boolean;
  uploadProgress: number;
}

const ProgressSection = ({ isProcessing, uploadProgress }: ProgressSectionProps) => {
  if (!isProcessing) return null;

  return (
    <div className="space-y-2">
      <ProgressHeader uploadProgress={uploadProgress} />
      <Progress value={uploadProgress} />
    </div>
  );
};

const ProgressHeader = ({ uploadProgress }: { uploadProgress: number }) => {
  return (
    <div className="flex justify-between text-sm">
      <span>Processing...</span>
      <span>{uploadProgress}%</span>
    </div>
  );
};

interface ActionButtonsProps {
  isProcessing: boolean;
  onStartIngestion: () => void;
}

const ActionButtons = ({ isProcessing, onStartIngestion }: ActionButtonsProps) => {
  return (
    <div className="flex gap-4">
      <StartIngestionButton 
        isProcessing={isProcessing} 
        onStartIngestion={onStartIngestion} 
      />
      <ScheduleButton isProcessing={isProcessing} />
    </div>
  );
};

const StartIngestionButton = ({ isProcessing, onStartIngestion }: ActionButtonsProps) => {
  return (
    <Button onClick={onStartIngestion} disabled={isProcessing}>
      {isProcessing ? (
        <>
          <Clock className="mr-2 h-4 w-4 animate-spin" />
          Processing...
        </>
      ) : (
        <>
          <Play className="mr-2 h-4 w-4" />
          Start Ingestion
        </>
      )}
    </Button>
  );
};

const ScheduleButton = ({ isProcessing }: { isProcessing: boolean }) => {
  return (
    <Button variant="outline" disabled={isProcessing}>
      <Pause className="mr-2 h-4 w-4" />
      Schedule
    </Button>
  );
};