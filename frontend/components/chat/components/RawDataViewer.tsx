import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, ChevronRight, Code } from 'lucide-react';
import type { FinalReportData, ExpandedSections } from '../types/FinalReportTypes';

interface RawDataViewerProps {
  reportData: FinalReportData;
  isExpanded: boolean;
  onToggle: () => void;
}

// Format report data for display
const formatReportData = (reportData: FinalReportData): string => {
  return JSON.stringify(reportData, null, 2);
};

// Get appropriate chevron icon
const getChevronIcon = (isExpanded: boolean): React.ReactNode => {
  return isExpanded ? 
    <ChevronDown className="w-4 h-4" /> : 
    <ChevronRight className="w-4 h-4" />;
};

// Main RawDataViewer component
export const RawDataViewer: React.FC<RawDataViewerProps> = ({ 
  reportData, 
  isExpanded, 
  onToggle 
}) => (
  <Collapsible open={isExpanded} onOpenChange={onToggle}>
    <Card>
      <CollapsibleTrigger className="w-full">
        <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
          <CardTitle className="flex items-center gap-2 text-base">
            {getChevronIcon(isExpanded)}
            <Code className="w-4 h-4" />
            Raw Report Data
          </CardTitle>
        </CardHeader>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <CardContent>
          <div className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto">
            <pre className="text-xs">
              {formatReportData(reportData)}
            </pre>
          </div>
        </CardContent>
      </CollapsibleContent>
    </Card>
  </Collapsible>
);