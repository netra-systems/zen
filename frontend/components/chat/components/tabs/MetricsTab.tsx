import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { LineChart, Code } from 'lucide-react';
import type { ExecutionMetrics, ToolCall } from '@/types/unified/metrics.types';
import { formatDuration } from '../../utils/reportUtils';

interface MetricsTabProps {
  executionMetrics?: ExecutionMetrics;
}

// Check if tool calls exist
const hasToolCalls = (executionMetrics?: ExecutionMetrics): boolean => {
  return Boolean(executionMetrics?.tool_calls?.length);
};

// Tool usage row component
const ToolUsageRow: React.FC<{ tool: ToolCall }> = ({ tool }) => (
  <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
    <div className="flex items-center gap-3">
      <Code className="w-4 h-4 text-gray-600" />
      <span className="font-medium">{tool.tool_name}</span>
    </div>
    <div className="flex items-center gap-4">
      <Badge variant="secondary">{tool.count} calls</Badge>
      <Badge variant="outline">avg {formatDuration(tool.avg_duration)}</Badge>
    </div>
  </div>
);

// Tool usage statistics component
const ToolUsageStats: React.FC<{ toolCalls: ToolCall[] }> = ({ toolCalls }) => (
  <Card>
    <CardHeader>
      <CardTitle className="flex items-center gap-2">
        <LineChart className="w-5 h-5 text-purple-600" />
        Tool Usage Statistics
      </CardTitle>
    </CardHeader>
    <CardContent>
      <div className="space-y-3">
        {toolCalls.map((tool, idx) => (
          <ToolUsageRow key={idx} tool={tool} />
        ))}
      </div>
    </CardContent>
  </Card>
);

// Main MetricsTab component
export const MetricsTab: React.FC<MetricsTabProps> = ({ executionMetrics }) => {
  if (!hasToolCalls(executionMetrics)) {
    return (
      <div className="text-center text-gray-500 py-8">
        No metrics data available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <ToolUsageStats toolCalls={executionMetrics!.tool_calls} />
    </div>
  );
};