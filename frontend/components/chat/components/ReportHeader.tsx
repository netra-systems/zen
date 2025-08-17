import React from 'react';
import { Card, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Copy } from 'lucide-react';
import type { FinalReportData } from '../types/FinalReportTypes';
import { downloadReport, copyToClipboard } from '../utils/reportUtils';

interface ReportHeaderProps {
  reportData: FinalReportData;
}

// Handle copy action with JSON stringification
const handleCopy = (reportData: FinalReportData): void => {
  copyToClipboard(JSON.stringify(reportData));
};

// Handle download action
const handleDownload = (reportData: FinalReportData): void => {
  downloadReport(reportData);
};

// Render action buttons
const ActionButtons: React.FC<ReportHeaderProps> = ({ reportData }) => (
  <div className="flex gap-2">
    <Button variant="outline" size="sm" onClick={() => handleDownload(reportData)}>
      <Download className="w-4 h-4 mr-1" />
      Download
    </Button>
    <Button variant="outline" size="sm" onClick={() => handleCopy(reportData)}>
      <Copy className="w-4 h-4 mr-1" />
      Copy
    </Button>
  </div>
);

// Get current timestamp for report
const getCurrentTimestamp = (): string => {
  return new Date().toLocaleString();
};

// Main ReportHeader component
export const ReportHeader: React.FC<ReportHeaderProps> = ({ reportData }) => (
  <Card className="glass-card border-emerald-200">
    <CardHeader>
      <div className="flex justify-between items-start">
        <div>
          <CardTitle className="text-2xl font-bold text-gray-900">
            Optimization Analysis Report
          </CardTitle>
          <p className="text-sm text-gray-600 mt-2">
            Generated at {getCurrentTimestamp()}
          </p>
        </div>
        <ActionButtons reportData={reportData} />
      </div>
    </CardHeader>
  </Card>
);