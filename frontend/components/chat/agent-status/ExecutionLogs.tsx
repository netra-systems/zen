"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { motion, AnimatePresence } from 'framer-motion';
import { ExecutionLogsProps } from './types';

const renderLogsHeader = (showLogs: boolean, onToggleLogs: () => void) => {
  return (
    <div className="flex items-center justify-between mb-2">
      <h4 className="text-sm font-semibold">Execution Logs</h4>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2"
        onClick={onToggleLogs}
      >
        {showLogs ? 'Hide' : 'Show'}
      </Button>
    </div>
  );
};

const renderLogsContent = (logs: string[]) => {
  return (
    <motion.div
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
      className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto"
    >
      <pre className="text-xs text-gray-300 font-mono">
        {logs.join('\n')}
      </pre>
    </motion.div>
  );
};

const renderAnimatedLogs = (showLogs: boolean, logs: string[]) => {
  return (
    <AnimatePresence>
      {showLogs && renderLogsContent(logs)}
    </AnimatePresence>
  );
};

export const ExecutionLogs: React.FC<ExecutionLogsProps> = ({ logs }) => {
  const [showLogs, setShowLogs] = useState(false);

  if (logs.length === 0) return null;

  const toggleLogs = () => setShowLogs(!showLogs);

  return (
    <div>
      {renderLogsHeader(showLogs, toggleLogs)}
      {renderAnimatedLogs(showLogs, logs)}
    </div>
  );
};