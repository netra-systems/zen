import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { TrendingUp, ChevronDown, ChevronRight } from 'lucide-react';
import type { ExpandedSections } from '../../types/FinalReportTypes';

interface OptimizationsTabProps {
  optimizationsResult?: Record<string, unknown>;
  expandedSections: ExpandedSections;
  toggleSection: (section: string) => void;
}

// Check if optimizations result exists
const hasOptimizations = (optimizationsResult?: Record<string, unknown>): boolean => {
  return Boolean(optimizationsResult && Object.keys(optimizationsResult).length > 0);
};

// Format key for display
const formatKey = (key: string): string => {
  return key.replace(/_/g, ' ');
};

// Format value for display
const formatValue = (value: unknown): string => {
  return JSON.stringify(value, null, 2);
};

// Optimization section component
const OptimizationSection: React.FC<{
  sectionKey: string;
  value: unknown;
  isExpanded: boolean;
  onToggle: () => void;
}> = ({ sectionKey, value, isExpanded, onToggle }) => (
  <Collapsible open={isExpanded} onOpenChange={onToggle}>
    <CollapsibleTrigger className="flex items-center gap-2 w-full p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      <span className="font-medium capitalize">{formatKey(sectionKey)}</span>
    </CollapsibleTrigger>
    <CollapsibleContent className="mt-2 p-3 bg-white border rounded-lg">
      <pre className="text-sm overflow-x-auto">
        {formatValue(value)}
      </pre>
    </CollapsibleContent>
  </Collapsible>
);

// Main OptimizationsTab component
export const OptimizationsTab: React.FC<OptimizationsTabProps> = ({ 
  optimizationsResult, 
  expandedSections, 
  toggleSection 
}) => {
  if (!hasOptimizations(optimizationsResult)) {
    return (
      <div className="text-center text-gray-500 py-8">
        No optimization recommendations available
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-green-600" />
          Optimization Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.entries(optimizationsResult!).map(([key, value]) => (
            <OptimizationSection
              key={key}
              sectionKey={key}
              value={value}
              isExpanded={expandedSections[key]}
              onToggle={() => toggleSection(key)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};