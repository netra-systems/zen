"use client";

import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Cpu, HardDrive, Zap, Sparkles } from 'lucide-react';
import { ResourceMetricsProps } from './types';

const renderMetricIcon = (type: 'cpu' | 'memory' | 'api' | 'tokens') => {
  switch (type) {
    case 'cpu':
      return <Cpu className="w-3 h-3" />;
    case 'memory':
      return <HardDrive className="w-3 h-3" />;
    case 'api':
      return <Zap className="w-3 h-3" />;
    case 'tokens':
      return <Sparkles className="w-3 h-3" />;
  }
};

const renderMetricHeader = (type: 'cpu' | 'memory' | 'api' | 'tokens', label: string) => {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
      {renderMetricIcon(type)}
      <span>{label}</span>
    </div>
  );
};

const renderProgressMetric = (value: number, progress: number) => {
  return (
    <div className="flex items-center gap-2">
      <div className="text-lg font-semibold">{value}%</div>
      <div className="flex-1">
        <Progress value={progress} className="h-1" />
      </div>
    </div>
  );
};

const renderValueMetric = (value: number | string) => {
  return (
    <div className="text-lg font-semibold">{value}</div>
  );
};

const renderCpuMetric = (cpu: number) => {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      {renderMetricHeader('cpu', 'CPU Usage')}
      {renderProgressMetric(cpu, cpu)}
    </div>
  );
};

const renderMemoryMetric = (memory: number) => {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      {renderMetricHeader('memory', 'Memory')}
      {renderProgressMetric(memory, memory)}
    </div>
  );
};

const renderApiCallsMetric = (apiCalls: number) => {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      {renderMetricHeader('api', 'API Calls')}
      {renderValueMetric(apiCalls)}
    </div>
  );
};

const renderTokensMetric = (tokensUsed: number) => {
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      {renderMetricHeader('tokens', 'Tokens')}
      {renderValueMetric(tokensUsed.toLocaleString())}
    </div>
  );
};

const renderMetricsGrid = (metrics: any) => {
  return (
    <div className="grid grid-cols-2 gap-3">
      {metrics.cpu !== undefined && renderCpuMetric(metrics.cpu)}
      {metrics.memory !== undefined && renderMemoryMetric(metrics.memory)}
      {metrics.apiCalls !== undefined && renderApiCallsMetric(metrics.apiCalls)}
      {metrics.tokensUsed !== undefined && renderTokensMetric(metrics.tokensUsed)}
    </div>
  );
};

export const ResourceMetrics: React.FC<ResourceMetricsProps> = ({ metrics }) => {
  const hasMetrics = Object.keys(metrics).length > 0;
  
  if (!hasMetrics) return null;

  return (
    <div className="mb-4">
      <h4 className="text-sm font-semibold mb-2">Resource Usage</h4>
      {renderMetricsGrid(metrics)}
    </div>
  );
};