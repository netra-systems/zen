"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Terminal, Loader2 } from 'lucide-react';
import { ToolExecutionProps, Tool } from './types';
import { getToolStatusClasses } from './constants';
import { formatTime } from './utils';

const renderToolIcon = () => {
  return <Terminal className="w-4 h-4 text-gray-500" />;
};

const renderToolDuration = (duration?: number) => {
  if (!duration) return null;
  
  return (
    <span className="text-xs text-gray-500">
      {formatTime(duration)}
    </span>
  );
};

const renderToolStatus = (status: string) => {
  const statusClasses = getToolStatusClasses(status);
  
  return (
    <Badge
      variant="outline"
      className={cn("text-xs", statusClasses)}
    >
      {status === 'running' && (
        <Loader2 className="w-3 h-3 mr-1 animate-spin" />
      )}
      {status}
    </Badge>
  );
};

const renderToolInfo = (tool: Tool) => {
  return (
    <div className="flex items-center gap-2">
      {renderToolIcon()}
      <span className="text-sm">{tool.name}</span>
    </div>
  );
};

const renderToolMetrics = (tool: Tool) => {
  return (
    <div className="flex items-center gap-2">
      {renderToolDuration(tool.duration)}
      {renderToolStatus(tool.status)}
    </div>
  );
};

const renderSingleTool = (tool: Tool, index: number) => {
  return (
    <div
      key={index}
      className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
    >
      {renderToolInfo(tool)}
      {renderToolMetrics(tool)}
    </div>
  );
};

const renderToolsList = (tools: Tool[]) => {
  return (
    <div className="space-y-2">
      {tools.map((tool, idx) => renderSingleTool(tool, idx))}
    </div>
  );
};

export const ToolExecution: React.FC<ToolExecutionProps> = ({ tools }) => {
  if (tools.length === 0) return null;

  return (
    <div className="mb-4">
      <h4 className="text-sm font-semibold mb-2">Tool Execution</h4>
      {renderToolsList(tools)}
    </div>
  );
};