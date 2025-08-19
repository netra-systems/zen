// MCP Tool Indicator Component - Shows MCP tool usage in chat messages
// Displays tool execution status, server info, and execution time

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Wrench, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Server, 
  Loader2,
  ChevronDown,
  ChevronRight 
} from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import type { MCPToolIndicatorProps } from '@/types/mcp-types';

// ============================================
// Helper Functions (8 lines max)
// ============================================

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'RUNNING': return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
    case 'COMPLETED': return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'FAILED': return <XCircle className="w-4 h-4 text-red-500" />;
    default: return <Clock className="w-4 h-4 text-gray-500" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'RUNNING': return 'border-blue-200 bg-blue-50';
    case 'COMPLETED': return 'border-green-200 bg-green-50';
    case 'FAILED': return 'border-red-200 bg-red-50';
    default: return 'border-gray-200 bg-gray-50';
  }
};

const formatDuration = (ms: number | undefined): string => {
  if (!ms) return 'N/A';
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
};

const formatArgs = (args: Record<string, any> | undefined | null): string => {
  if (!args) return 'No arguments';
  const entries = Object.entries(args);
  if (entries.length === 0) return 'No arguments';
  return entries.slice(0, 2).map(([k, v]) => `${k}: ${String(v).slice(0, 20)}`).join(', ');
};

// ============================================
// Sub-components (8 lines max)
// ============================================

const ToolExecutionCard: React.FC<{ execution: any; isExpanded: boolean; onToggle: () => void }> = ({ 
  execution, 
  isExpanded, 
  onToggle 
}) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    className={`p-3 rounded-lg border ${getStatusColor(execution.status)}`}
  >
    <div className="flex items-center justify-between">
      <div className="flex items-center space-x-2">
        {getStatusIcon(execution.status)}
        <span className="font-medium text-sm">{execution.tool_name}</span>
        <span className="text-xs text-gray-500">@{execution.server_name}</span>
      </div>
      <div className="flex items-center space-x-2">
        <span className="text-xs text-gray-500">{formatDuration(execution.duration_ms)}</span>
        <button onClick={onToggle} className="text-gray-400 hover:text-gray-600">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>
    </div>
    
    <Collapsible open={isExpanded}>
      <CollapsibleContent className="mt-2 space-y-2">
        <div className="text-xs text-gray-600">
          <div><strong>Arguments:</strong> {formatArgs(execution.arguments)}</div>
          {execution.result && (
            <div className="mt-1"><strong>Result:</strong> {execution.result.content?.length || 0} items</div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  </motion.div>
);

const ServerStatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <div className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${
    status === 'CONNECTED' ? 'bg-green-100 text-green-800' : 
    status === 'DISCONNECTED' ? 'bg-red-100 text-red-800' : 
    'bg-yellow-100 text-yellow-800'
  }`}>
    <Server className="w-3 h-3" />
    <span>{status}</span>
  </div>
);

// ============================================
// Main Component
// ============================================

export const MCPToolIndicator: React.FC<MCPToolIndicatorProps> = ({
  tool_executions = [],
  server_status,
  show_details = false,
  className = ''
}) => {
  const [expandedExecutions, setExpandedExecutions] = React.useState<Set<string>>(new Set());

  const toggleExecution = React.useCallback((executionId: string) => {
    setExpandedExecutions(prev => {
      const newSet = new Set(prev);
      if (newSet.has(executionId)) {
        newSet.delete(executionId);
      } else {
        newSet.add(executionId);
      }
      return newSet;
    });
  }, []);

  const summary = useMemo(() => {
    const running = tool_executions.filter(e => e.status === 'RUNNING').length;
    const completed = tool_executions.filter(e => e.status === 'COMPLETED').length;
    const failed = tool_executions.filter(e => e.status === 'FAILED').length;
    return { running, completed, failed, total: tool_executions.length };
  }, [tool_executions]);

  if (tool_executions.length === 0) return null;

  return (
    <div className={`mcp-tool-indicator ${className}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center space-x-2">
          <Wrench className="w-4 h-4 text-purple-500" />
          <span className="text-sm font-medium text-gray-700">
            MCP Tools ({summary.total})
          </span>
        </div>
        <ServerStatusBadge status={server_status} />
      </div>

      {summary.running > 0 && (
        <div className="text-xs text-blue-600 mb-2">
          {summary.running} tool{summary.running > 1 ? 's' : ''} executing...
        </div>
      )}

      <AnimatePresence>
        {tool_executions.map((execution) => (
          <div key={execution.id} className="mb-2 last:mb-0">
            <ToolExecutionCard
              execution={execution}
              isExpanded={expandedExecutions.has(execution.id)}
              onToggle={() => toggleExecution(execution.id)}
            />
          </div>
        ))}
      </AnimatePresence>

      {show_details && summary.total > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-200">
          <div className="flex justify-between text-xs text-gray-500">
            <span>✓ {summary.completed} completed</span>
            <span>✗ {summary.failed} failed</span>
          </div>
        </div>
      )}
    </div>
  );
};

MCPToolIndicator.displayName = 'MCPToolIndicator';