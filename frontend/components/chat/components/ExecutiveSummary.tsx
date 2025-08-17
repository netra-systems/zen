import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText } from 'lucide-react';
import type { FinalReportData } from '../types/FinalReportTypes';

interface ExecutiveSummaryProps {
  finalReport?: string;
}

// Check if final report exists and has content
const hasFinalReport = (finalReport?: string): boolean => {
  return Boolean(finalReport?.trim());
};

// Main ExecutiveSummary component
export const ExecutiveSummary: React.FC<ExecutiveSummaryProps> = ({ finalReport }) => {
  if (!hasFinalReport(finalReport)) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-blue-600" />
          Executive Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="prose max-w-none">
          <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {finalReport}
          </p>
        </div>
      </CardContent>
    </Card>
  );
};