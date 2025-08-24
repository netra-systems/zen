// Execution Metrics Section Component
// Business Value: Performance metrics visibility for all customer segments

import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Clock, TrendingUp, CheckCircle } from 'lucide-react';
import { formatDuration } from './slow-layer-utils';
import type { ExecutionMetrics } from '@/types/unified/metrics.types';

interface ExecutionMetricsSectionProps {
  metrics: ExecutionMetrics;
  completedAgents?: any[];
  totalDuration?: number;
}

export const ExecutionMetricsSection: React.FC<ExecutionMetricsSectionProps> = ({ 
  metrics,
  completedAgents,
  totalDuration
}) => {
  if (!metrics) {
    return null;
  }

  return (
    <div>
      <ExecutionMetricsHeader />
      <ExecutionMetricsGrid 
        metrics={metrics}
        completedAgents={completedAgents}
        totalDuration={totalDuration}
      />
    </div>
  );
};

const ExecutionMetricsHeader = () => (
  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
    <Cpu className="w-4 h-4 mr-2 text-indigo-600" />
    Execution Metrics
  </h3>
);

const ExecutionMetricsGrid = ({ metrics, completedAgents, totalDuration }: {
  metrics: ExecutionMetrics;
  completedAgents?: any[];
  totalDuration?: number;
}) => (
  <div className="bg-gradient-to-br from-white to-indigo-50/30 rounded-lg p-4 border border-indigo-200/50">
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <DurationMetric duration={metrics.total_duration_ms} />
      {metrics.total_tokens && <TokensMetric tokens={metrics.total_tokens} />}
      {metrics.total_cost !== undefined && <CostMetric cost={metrics.total_cost} />}
      {metrics.cache_efficiency !== undefined && (
        <CacheEfficiencyMetric efficiency={metrics.cache_efficiency} />
      )}
      {completedAgents && <AgentsRunMetric agentCount={completedAgents.length} />}
      {totalDuration && completedAgents && (
        <AveragePerAgentMetric 
          totalDuration={totalDuration}
          agentCount={completedAgents.length}
        />
      )}
    </div>
  </div>
);

const DurationMetric = ({ duration }: { duration: number }) => (
  <MetricCard
    title="Total Duration"
    icon={<Clock className="w-3 h-3 text-gray-400" />}
    value={formatDuration(duration)}
  />
);

const TokensMetric = ({ tokens }: { tokens: number }) => (
  <MetricCard
    title="Tokens Used"
    icon={<TrendingUp className="w-3 h-3 text-gray-400" />}
    value={tokens.toLocaleString()}
  />
);

const CostMetric = ({ cost }: { cost: number }) => (
  <MetricCard
    title="Est. Cost"
    icon={<span className="text-xs text-green-600">💰</span>}
    value={`$${cost.toFixed(4)}`}
  />
);

const CacheEfficiencyMetric = ({ efficiency }: { efficiency: number }) => (
  <MetricCard
    title="Cache Hit Rate"
    icon={<span className="text-xs">⚡</span>}
    value={`${(efficiency * 100).toFixed(1)}%`}
  />
);

const AgentsRunMetric = ({ agentCount }: { agentCount: number }) => (
  <MetricCard
    title="Agents Run"
    icon={<CheckCircle className="w-3 h-3 text-green-500" />}
    value={agentCount.toString()}
  />
);

const AveragePerAgentMetric = ({ totalDuration, agentCount }: { 
  totalDuration: number; 
  agentCount: number; 
}) => (
  <MetricCard
    title="Avg per Agent"
    icon={<span className="text-xs">📊</span>}
    value={formatDuration(Math.round(totalDuration / agentCount))}
  />
);

const MetricCard = ({ title, icon, value }: {
  title: string;
  icon: React.ReactNode;
  value: string;
}) => (
  <motion.div 
    className="bg-white/70 rounded-lg p-3 border border-gray-200/50"
    whileHover={{ scale: 1.02 }}
    transition={{ duration: 0.2 }}
  >
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-gray-600">{title}</span>
      {icon}
    </div>
    <div className="font-mono text-lg font-semibold text-gray-800 mt-1">
      {value}
    </div>
  </motion.div>
);