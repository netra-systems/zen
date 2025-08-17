"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { AgentStatusCardProps } from './types';
import { getRingClasses } from './constants';
import { AgentHeader } from './AgentHeader';
import { ToolExecution } from './ToolExecution';
import { ResourceMetrics } from './ResourceMetrics';
import { ExecutionLogs } from './ExecutionLogs';

const useElapsedTime = (status: string) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const startTimeRef = React.useRef(Date.now());

  useEffect(() => {
    if (status === 'executing' || status === 'thinking') {
      const interval = setInterval(() => {
        setElapsedTime(Date.now() - startTimeRef.current);
      }, 1000);
      return () => clearInterval(interval);
    } else {
      startTimeRef.current = Date.now();
      setElapsedTime(0);
    }
  }, [status]);

  return elapsedTime;
};

const renderCardContent = (
  isExpanded: boolean,
  tools: any[],
  metrics: any,
  logs: string[]
) => {
  if (!isExpanded) return null;

  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <CardContent className="pt-0">
        <ToolExecution tools={tools} />
        <ResourceMetrics metrics={metrics} />
        <ExecutionLogs logs={logs} />
      </CardContent>
    </motion.div>
  );
};

const getCardClasses = (status: string) => {
  return cn(
    "overflow-hidden transition-all duration-300",
    "hover:shadow-lg",
    getRingClasses(status)
  );
};

export const AgentStatusCard: React.FC<AgentStatusCardProps> = ({
  agentName,
  status,
  currentAction,
  progress = 0,
  eta,
  tools = [],
  metrics = {},
  logs = [],
  onCancel,
  onPause,
  onResume,
  isPaused = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const elapsedTime = useElapsedTime(status);

  const toggleExpanded = () => setIsExpanded(!isExpanded);

  return (
    <Card className={getCardClasses(status)}>
      <AgentHeader
        agentName={agentName}
        status={status}
        currentAction={currentAction}
        progress={progress}
        eta={eta}
        elapsedTime={elapsedTime}
        isPaused={isPaused}
        isExpanded={isExpanded}
        onCancel={onCancel}
        onPause={onPause}
        onResume={onResume}
        onToggleExpand={toggleExpanded}
      />

      <AnimatePresence>
        {renderCardContent(isExpanded, tools, metrics, logs)}
      </AnimatePresence>
    </Card>
  );
};