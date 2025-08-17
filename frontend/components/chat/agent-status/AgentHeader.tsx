"use client";

import React from 'react';
import { CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  X
} from 'lucide-react';
import { AgentHeaderProps } from './types';
import { agentIcons, statusColors, statusAnimations, getGradientClasses } from './constants';
import { formatTime, getStatusIcon, getAnimationConfig } from './utils';

const renderAgentAvatar = (agentName: string, status: string) => {
  const AgentIcon = agentIcons[agentName] || agentIcons['Default'];
  const gradientClasses = getGradientClasses(status);
  const animationConfig = getAnimationConfig(status);
  
  return (
    <motion.div
      animate={statusAnimations[status]}
      transition={animationConfig}
      className={cn(
        "p-3 rounded-xl bg-gradient-to-br",
        gradientClasses
      )}
    >
      <AgentIcon className="w-6 h-6 text-white" />
    </motion.div>
  );
};

const renderStatusBadge = (status: string, isPaused: boolean) => {
  const statusColor = statusColors[status];
  const displayStatus = isPaused ? 'Paused' : status;
  
  return (
    <Badge className={cn("text-xs", statusColor)}>
      {getStatusIcon(status)}
      <span className="ml-1 capitalize">{displayStatus}</span>
    </Badge>
  );
};

const renderTimingInfo = (elapsedTime: number, eta?: number) => {
  return (
    <>
      {elapsedTime > 0 && (
        <span className="text-xs text-gray-500">
          {formatTime(elapsedTime)}
        </span>
      )}
      {eta && (
        <span className="text-xs text-gray-500">
          ETA: {formatTime(eta)}
        </span>
      )}
    </>
  );
};

const renderControlButtons = (
  status: string,
  isPaused: boolean,
  onPause?: () => void,
  onResume?: () => void,
  onCancel?: () => void
) => {
  const isActive = status === 'executing' || status === 'thinking';
  
  if (!isActive) return null;
  
  return (
    <>
      {isPaused ? (
        <Button
          variant="ghost"
          size="icon"
          className="w-8 h-8"
          onClick={onResume}
        >
          <Play className="w-4 h-4" />
        </Button>
      ) : (
        <Button
          variant="ghost"
          size="icon"
          className="w-8 h-8"
          onClick={onPause}
        >
          <Pause className="w-4 h-4" />
        </Button>
      )}
      <Button
        variant="ghost"
        size="icon"
        className="w-8 h-8 text-red-500 hover:text-red-600"
        onClick={onCancel}
      >
        <X className="w-4 h-4" />
      </Button>
    </>
  );
};

const renderExpandButton = (isExpanded: boolean, onToggleExpand: () => void) => {
  return (
    <Button
      variant="ghost"
      size="icon"
      className="w-8 h-8"
      onClick={onToggleExpand}
    >
      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
    </Button>
  );
};

const renderCurrentAction = (currentAction?: string) => {
  if (!currentAction) return null;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 p-2 bg-gray-50 rounded-lg"
    >
      <p className="text-sm text-gray-600">{currentAction}</p>
    </motion.div>
  );
};

const renderProgressBar = (status: string, progress: number) => {
  const isActive = status === 'executing' || status === 'thinking';
  
  if (!isActive || progress <= 0) return null;
  
  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500">Progress</span>
        <span className="text-xs font-medium">{Math.round(progress)}%</span>
      </div>
      <Progress value={progress} className="h-2" />
    </div>
  );
};

export const AgentHeader: React.FC<AgentHeaderProps> = ({
  agentName,
  status,
  currentAction,
  progress = 0,
  eta,
  elapsedTime,
  isPaused = false,
  isExpanded,
  onCancel,
  onPause,
  onResume,
  onToggleExpand
}) => {
  return (
    <CardHeader className="pb-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          {renderAgentAvatar(agentName, status)}
          
          <div>
            <CardTitle className="text-lg font-semibold">{agentName}</CardTitle>
            <div className="flex items-center gap-2 mt-1">
              {renderStatusBadge(status, isPaused)}
              {renderTimingInfo(elapsedTime, eta)}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {renderControlButtons(status, isPaused, onPause, onResume, onCancel)}
          {renderExpandButton(isExpanded, onToggleExpand)}
        </div>
      </div>

      {renderCurrentAction(currentAction)}
      {renderProgressBar(status, progress)}
    </CardHeader>
  );
};