import React from 'react';
import {
  Clock,
  Loader2,
  Activity,
  CheckCircle,
  AlertCircle,
  X,
  Bot
} from 'lucide-react';
import { AgentStatus } from '@/types/unified';

export const convertMsToTimeUnits = (ms: number) => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  return { seconds, minutes, hours };
};

export const formatTimeString = (hours: number, minutes: number, seconds: number): string => {
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
};

export const formatTime = (ms: number): string => {
  const { seconds, minutes, hours } = convertMsToTimeUnits(ms);
  return formatTimeString(hours, minutes, seconds);
};

export const getIdleIcon = () => <Clock className="w-4 h-4" />;

export const getThinkingIcon = () => <Loader2 className="w-4 h-4 animate-spin" />;

export const getExecutingIcon = () => <Activity className="w-4 h-4" />;

export const getSuccessIcon = () => <CheckCircle className="w-4 h-4" />;

export const getErrorIcon = () => <AlertCircle className="w-4 h-4" />;

export const getCancelledIcon = () => <X className="w-4 h-4" />;

export const getDefaultIcon = () => <Bot className="w-4 h-4" />;

const getStatusIconForIdleStates = (status: AgentStatus): React.ReactElement | null => {
  if (status === 'idle') return getIdleIcon();
  if (status === 'thinking') return getThinkingIcon();
  if (status === 'executing') return getExecutingIcon();
  return null;
};

const getStatusIconForFinalStates = (status: AgentStatus): React.ReactElement | null => {
  if (status === 'success') return getSuccessIcon();
  if (status === 'error') return getErrorIcon();
  if (status === 'cancelled') return getCancelledIcon();
  return null;
};

export const getStatusIcon = (status: AgentStatus): React.ReactElement => {
  return getStatusIconForIdleStates(status) || 
         getStatusIconForFinalStates(status) || 
         getDefaultIcon();
};

const getThinkingAnimationConfig = () => {
  return { duration: 2, repeat: Infinity };
};

const getExecutingAnimationConfig = () => {
  return { duration: 3, repeat: Infinity, ease: "linear" };
};

export const getAnimationConfig = (status: AgentStatus) => {
  if (status === 'thinking') return getThinkingAnimationConfig();
  if (status === 'executing') return getExecutingAnimationConfig();
  return {};
};