import React from 'react';
import { Brain, TrendingUp, Settings, Database, Zap, Activity, CheckCircle2, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { StatusZone, WorkflowProgress, ToolExecutionStatus, Metrics } from './types';

export const createCurrentPhaseZone = (subAgentName: string | null, now: number): StatusZone => ({
  type: 'slow',
  label: 'Current Phase',
  content: subAgentName || 'Initializing',
  icon: React.createElement(Brain, { className: "w-4 h-4" }),
  lastUpdate: now,
  color: 'text-purple-600'
});

export const createProgressContent = (progress: WorkflowProgress): React.ReactNode => (
  React.createElement('div', { className: "flex items-center space-x-2" },
    React.createElement('div', { className: "flex-1 bg-gray-200 rounded-full h-2" },
      React.createElement(motion.div, {
        className: "bg-gradient-to-r from-emerald-500 to-purple-600 h-2 rounded-full",
        initial: { width: 0 },
        animate: { width: `${(progress.current_step / progress.total_steps) * 100}%` },
        transition: { duration: 0.5 }
      })
    ),
    React.createElement('span', { className: "text-xs font-mono" },
      `${progress.current_step}/${progress.total_steps}`
    )
  )
);

export const createProgressZone = (progress: WorkflowProgress, now: number): StatusZone => ({
  type: 'slow',
  label: 'Overall Progress',
  content: createProgressContent(progress),
  icon: React.createElement(TrendingUp, { className: "w-4 h-4" }),
  lastUpdate: now,
  color: 'text-blue-600'
});

export const createActiveToolsZone = (activeTools: string[], now: number): StatusZone => ({
  type: 'medium',
  label: 'Active Tools',
  content: activeTools.join(', ') || 'None',
  icon: React.createElement(Settings, { className: "w-4 h-4 animate-spin" }),
  lastUpdate: now,
  color: 'text-green-600'
});

export const createRecordsZone = (recordsProcessed: number, now: number): StatusZone => ({
  type: 'medium',
  label: 'Records Analyzed',
  content: `${recordsProcessed.toLocaleString()}`,
  icon: React.createElement(Database, { className: "w-4 h-4" }),
  lastUpdate: now,
  color: 'text-indigo-600'
});

export const createToolStatusContent = (status: ToolExecutionStatus): React.ReactNode => (
  React.createElement('div', { className: "flex items-center space-x-2" },
    status === 'executing'
      ? React.createElement(Loader2, { className: "w-3 h-3 animate-spin" })
      : React.createElement(CheckCircle2, { className: "w-3 h-3 text-green-500" }),
    React.createElement('span', { className: "text-xs capitalize" }, status)
  )
);

export const createToolStatusZone = (status: ToolExecutionStatus, now: number): StatusZone => ({
  type: 'fast',
  label: 'Tool Status',
  content: createToolStatusContent(status),
  icon: React.createElement(Zap, { className: "w-4 h-4" }),
  lastUpdate: now,
  color: 'text-yellow-600'
});

export const createProcessingRateZone = (rate: number, now: number): StatusZone => ({
  type: 'fast',
  label: 'Processing Rate',
  content: `${rate.toFixed(1)} ops/sec`,
  icon: React.createElement(Activity, { className: "w-4 h-4" }),
  lastUpdate: now,
  color: 'text-red-600'
});

export const generateSlowZones = (
  subAgentName: string | null,
  progress: WorkflowProgress,
  now: number
): StatusZone[] => {
  const zones: StatusZone[] = [];
  zones.push(createCurrentPhaseZone(subAgentName, now));
  if (progress.total_steps > 0) {
    zones.push(createProgressZone(progress, now));
  }
  return zones;
};

export const generateMediumZones = (
  activeTools: string[],
  metrics: Metrics,
  now: number
): StatusZone[] => {
  const zones: StatusZone[] = [];
  if (activeTools.length > 0) {
    zones.push(createActiveToolsZone(activeTools, now));
  }
  if (metrics.recordsProcessed > 0) {
    zones.push(createRecordsZone(metrics.recordsProcessed, now));
  }
  return zones;
};

export const generateFastZones = (
  toolStatus: ToolExecutionStatus,
  metrics: Metrics,
  now: number
): StatusZone[] => {
  const zones: StatusZone[] = [];
  if (toolStatus !== 'idle') {
    zones.push(createToolStatusZone(toolStatus, now));
  }
  if (metrics.processingRate > 0) {
    zones.push(createProcessingRateZone(metrics.processingRate, now));
  }
  return zones;
};

export const generateAllStatusZones = (
  subAgentName: string | null,
  progress: WorkflowProgress,
  activeTools: string[],
  toolStatus: ToolExecutionStatus,
  metrics: Metrics
): StatusZone[] => {
  const now = Date.now();
  return [
    ...generateSlowZones(subAgentName, progress, now),
    ...generateMediumZones(activeTools, metrics, now),
    ...generateFastZones(toolStatus, metrics, now)
  ];
};