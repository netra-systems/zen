import React from 'react';
import {
  Bot,
  Zap,
  Terminal,
  Target,
  Database,
  FileText
} from 'lucide-react';

export const agentIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  'TriageSubAgent': Target,
  'DataSubAgent': Database,
  'OptimizationsCoreSubAgent': Zap,
  'ActionsToMeetGoalsSubAgent': Terminal,
  'ReportingSubAgent': FileText,
  'Supervisor': Bot,
  'Default': Bot
};

export const statusColors: Record<string, string> = {
  idle: 'bg-gray-100 text-gray-600',
  thinking: 'bg-blue-100 text-blue-600',
  executing: 'bg-purple-100 text-purple-600',
  success: 'bg-green-100 text-green-600',
  error: 'bg-red-100 text-red-600',
  cancelled: 'bg-orange-100 text-orange-600'
};

export const statusAnimations: Record<string, { opacity?: number[], rotate?: number }> = {
  thinking: { opacity: [0.5, 1, 0.5] },
  executing: { rotate: 360 }
};

export const getGradientClasses = (status: string): string => {
  switch (status) {
    case 'idle':
      return 'from-gray-400 to-gray-500';
    case 'thinking':
      return 'from-blue-400 to-blue-600';
    case 'executing':
      return 'from-purple-400 to-purple-600';
    case 'success':
      return 'from-green-400 to-green-600';
    case 'error':
      return 'from-red-400 to-red-600';
    case 'cancelled':
      return 'from-orange-400 to-orange-600';
    default:
      return 'from-gray-400 to-gray-500';
  }
};

export const getRingClasses = (status: string): string => {
  switch (status) {
    case 'executing':
      return 'ring-2 ring-purple-500 ring-opacity-50';
    case 'thinking':
      return 'ring-2 ring-blue-500 ring-opacity-50';
    case 'error':
      return 'ring-2 ring-red-500 ring-opacity-50';
    default:
      return '';
  }
};

export const getToolStatusClasses = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'border-green-500 text-green-600';
    case 'running':
      return 'border-blue-500 text-blue-600';
    case 'failed':
      return 'border-red-500 text-red-600';
    case 'pending':
      return 'border-gray-300 text-gray-500';
    default:
      return 'border-gray-300 text-gray-500';
  }
};