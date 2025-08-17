import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Clock, Package, Zap } from 'lucide-react';
import type { ExecutionMetrics, AgentTiming } from '../../types/FinalReportTypes';
import { formatDuration } from '../../utils/reportUtils';

interface OverviewTabProps {
  executionMetrics?: ExecutionMetrics;
}

// Calculate total tool calls
const getTotalToolCalls = (executionMetrics?: ExecutionMetrics): number => {
  return executionMetrics?.tool_calls?.reduce((sum, t) => sum + t.count, 0) || 0;
};

// Get agent count
const getAgentCount = (executionMetrics?: ExecutionMetrics): number => {
  return executionMetrics?.agent_timings?.length || 0;
};

// Metric card component
const MetricCard: React.FC<{
  title: string;
  value: string;
  icon: React.ReactNode;
}> = ({ title, value, icon }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
        {icon}
      </div>
    </CardContent>
  </Card>
);

// Agent timing row component
const AgentTimingRow: React.FC<{
  timing: AgentTiming;
  totalDuration: number;
}> = ({ timing, totalDuration }) => {
  const progressValue = (timing.duration / totalDuration) * 100;
  
  return (
    <div className="flex items-center gap-4">
      <Badge variant="outline" className="min-w-[140px]">
        {timing.agent_name}
      </Badge>
      <div className="flex-1">
        <Progress value={progressValue} className="h-2" />
      </div>
      <span className="text-sm text-gray-600 min-w-[60px] text-right">
        {formatDuration(timing.duration)}
      </span>
    </div>
  );
};

// Agent timeline component
const AgentTimeline: React.FC<{
  agentTimings: AgentTiming[];
  totalDuration: number;
}> = ({ agentTimings, totalDuration }) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-lg">Agent Execution Timeline</CardTitle>
    </CardHeader>
    <CardContent className="space-y-3">
      {agentTimings.map((timing, idx) => (
        <AgentTimingRow 
          key={idx} 
          timing={timing} 
          totalDuration={totalDuration} 
        />
      ))}
    </CardContent>
  </Card>
);

// Metrics grid component
const MetricsGrid: React.FC<{ executionMetrics?: ExecutionMetrics }> = ({ 
  executionMetrics 
}) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    <MetricCard
      title="Total Duration"
      value={formatDuration(executionMetrics?.total_duration || 0)}
      icon={<Clock className="w-8 h-8 text-blue-500" />}
    />
    <MetricCard
      title="Agents Used"
      value={getAgentCount(executionMetrics).toString()}
      icon={<Package className="w-8 h-8 text-green-500" />}
    />
    <MetricCard
      title="Tool Calls"
      value={getTotalToolCalls(executionMetrics).toString()}
      icon={<Zap className="w-8 h-8 text-purple-500" />}
    />
  </div>
);

// Main OverviewTab component
export const OverviewTab: React.FC<OverviewTabProps> = ({ executionMetrics }) => (
  <div className="space-y-4">
    <MetricsGrid executionMetrics={executionMetrics} />
    
    {executionMetrics?.agent_timings && (
      <AgentTimeline 
        agentTimings={executionMetrics.agent_timings}
        totalDuration={executionMetrics.total_duration}
      />
    )}
  </div>
);