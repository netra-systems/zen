import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Database } from 'lucide-react';

interface DataAnalysisTabProps {
  dataResult?: Record<string, unknown>;
}

// Check if data result exists
const hasDataResult = (dataResult?: Record<string, unknown>): boolean => {
  return Boolean(dataResult && Object.keys(dataResult).length > 0);
};

// Format data result for display
const formatDataResult = (dataResult: Record<string, unknown>): string => {
  return JSON.stringify(dataResult, null, 2);
};

// Main DataAnalysisTab component
export const DataAnalysisTab: React.FC<DataAnalysisTabProps> = ({ dataResult }) => {
  if (!hasDataResult(dataResult)) {
    return (
      <div className="text-center text-gray-500 py-8">
        No data analysis results available
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="w-5 h-5 text-blue-600" />
          Data Analysis Results
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="bg-gray-50 rounded-lg p-4">
          <pre className="text-sm overflow-x-auto">
            {formatDataResult(dataResult!)}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
};