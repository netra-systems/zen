'use client';

import React from 'react';
import { useChatStore } from '@/store/chat';

interface SubAgentStatusProps {
  name?: string;
  status?: string;
}

export const SubAgentStatus = ({ name, status }: SubAgentStatusProps = {}) => {
  const store = useChatStore();
  const currentSubAgent = name || store?.currentSubAgent;
  const subAgentStatus = status || store?.subAgentStatus;
  const subAgentTools: string[] = []; // store?.subAgentTools || [];
  const subAgentProgress = undefined; // store?.subAgentProgress;
  const subAgentError = undefined; // store?.subAgentError;
  const subAgentDescription = undefined; // store?.subAgentDescription;
  const subAgentExecutionTime = undefined; // store?.subAgentExecutionTime;
  const queuedSubAgents: string[] = []; // store?.queuedSubAgents || [];

  // Don't render if no sub-agent is active
  if (!currentSubAgent) {
    return null;
  }

  // Determine status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PENDING': return 'bg-gray-500';
      case 'RUNNING': return 'bg-green-500';
      case 'COMPLETED': return 'bg-blue-500';
      case 'FAILED': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const isRunning = subAgentStatus === 'RUNNING';
  const statusColor = getStatusColor(subAgentStatus || 'PENDING');

  return (
    <div className="text-sm text-muted-foreground">
      <div className="flex items-center gap-2">
        <span 
          data-testid="status-indicator" 
          className={`w-2 h-2 rounded-full ${statusColor} ${isRunning ? 'animate-pulse' : ''}`}
        />
        <strong>{currentSubAgent}</strong>
        {subAgentStatus && <>: {subAgentStatus}</>}
      </div>
      
      {/* Error message */}
      {subAgentError && (
        <div className="text-red-500 mt-1">{subAgentError}</div>
      )}
      
      {/* Progress indicator */}
      {subAgentProgress && (
        <div className="mt-2">
          <div>Step {subAgentProgress.current} of {subAgentProgress.total}</div>
          <div>{subAgentProgress.message}</div>
          <div 
            role="progressbar" 
            aria-valuenow={(subAgentProgress.current / subAgentProgress.total) * 100}
            className="w-full bg-gray-200 rounded-full h-2 mt-1"
          >
            <div 
              className="bg-blue-500 h-2 rounded-full" 
              style={{ width: `${(subAgentProgress.current / subAgentProgress.total) * 100}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Tools being used */}
      {subAgentTools && subAgentTools.length > 0 && (
        <div className="mt-2">
          <span>Tools: </span>
          {subAgentTools.map((tool, index) => (
            <span key={tool}>
              {tool}{index < subAgentTools.length - 1 && ', '}
            </span>
          ))}
        </div>
      )}
      
      {/* Execution time */}
      {subAgentExecutionTime && subAgentStatus === 'COMPLETED' && (
        <div className="mt-1">
          Completed in {(subAgentExecutionTime / 1000).toFixed(2)}s
        </div>
      )}
      
      {/* Queued agents */}
      {queuedSubAgents && queuedSubAgents.length > 0 && (
        <div className="mt-1">
          Next: {queuedSubAgents[0]}
          {queuedSubAgents.length > 1 && ` → ${queuedSubAgents.length - 1} more`}
        </div>
      )}
      
      {/* Description tooltip (simplified version) */}
      {subAgentDescription && (
        <div className="hidden hover:block absolute bg-gray-800 text-white p-2 rounded">
          {subAgentDescription}
        </div>
      )}
    </div>
  );
};
