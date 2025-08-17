import type { FinalReportData } from '../types/FinalReportTypes';

// Format duration from milliseconds to readable string
export const formatDuration = (ms: number): string => {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
};

// Copy text to clipboard
export const copyToClipboard = (text: string): void => {
  navigator.clipboard.writeText(text);
};

// Create blob from report data
const createReportBlob = (reportData: FinalReportData): Blob => {
  return new Blob([JSON.stringify(reportData, null, 2)], { 
    type: 'application/json' 
  });
};

// Create download URL from blob
const createDownloadUrl = (blob: Blob): string => {
  return URL.createObjectURL(blob);
};

// Trigger download of file
const triggerDownload = (url: string, filename: string): void => {
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
};

// Clean up URL after download
const cleanupUrl = (url: string): void => {
  URL.revokeObjectURL(url);
};

// Generate filename with timestamp
const generateFilename = (): string => {
  return `netra-report-${Date.now()}.json`;
};

// Main download function - orchestrates the download process
export const downloadReport = (reportData: FinalReportData): void => {
  const blob = createReportBlob(reportData);
  const url = createDownloadUrl(blob);
  const filename = generateFilename();
  triggerDownload(url, filename);
  cleanupUrl(url);
};