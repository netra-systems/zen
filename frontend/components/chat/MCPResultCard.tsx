// MCP Result Card Component - Formats and displays MCP tool execution results
// Shows structured data with collapsible sections and error handling

import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  Code, 
  ChevronDown, 
  ChevronRight,
  FileText,
  AlertCircle,
  Copy,
  ExternalLink
} from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';
import type { MCPResultCardProps } from '@/types/mcp-types';

// ============================================
// Helper Functions (8 lines max)
// ============================================

const getStatusIcon = (isError: boolean) => {
  return isError 
    ? <XCircle className="w-5 h-5 text-red-500" />
    : <CheckCircle className="w-5 h-5 text-green-500" />;
};

const getStatusColor = (isError: boolean) => {
  return isError 
    ? 'border-red-200 bg-red-50'
    : 'border-green-200 bg-green-50';
};

const formatDuration = (ms: number | undefined): string => {
  if (!ms) return 'N/A';
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
};

const formatContentType = (content: any): string => {
  if (typeof content === 'string') return 'text';
  if (Array.isArray(content)) return `array[${content.length}]`;
  if (typeof content === 'object') return 'object';
  return typeof content;
};

// ============================================
// Sub-components (8 lines max)
// ============================================

const ResultHeader: React.FC<{ result: any; execution: any }> = ({ result, execution }) => (
  <div className="flex items-center justify-between p-3 border-b border-gray-200">
    <div className="flex items-center space-x-2">
      {getStatusIcon(result.is_error)}
      <span className="font-medium text-sm">{result.tool_name}</span>
      <span className="text-xs text-gray-500">@{result.server_name}</span>
    </div>
    <div className="flex items-center space-x-2 text-xs text-gray-500">
      <Clock className="w-3 h-3" />
      <span>{formatDuration(result.execution_time_ms)}</span>
    </div>
  </div>
);

const ErrorDisplay: React.FC<{ errorMessage: string }> = ({ errorMessage }) => (
  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
    <div className="flex items-start space-x-2">
      <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-red-800">Execution Error</p>
        <p className="text-sm text-red-700 mt-1">{errorMessage}</p>
      </div>
    </div>
  </div>
);

const ContentItem: React.FC<{ item: any; index: number }> = ({ item, index }) => (
  <div className="p-3 bg-gray-50 rounded border border-gray-200">
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs font-medium text-gray-600">Item {index + 1}</span>
      <span className="text-xs text-gray-500">{formatContentType(item)}</span>
    </div>
    <div className="text-sm text-gray-800">
      {typeof item === 'string' ? (
        <p>{item}</p>
      ) : (
        <RawJsonView data={item} />
      )}
    </div>
  </div>
);

const ContentDisplay: React.FC<{ content: any[] }> = ({ content }) => {
  if (!content || content.length === 0) {
    return (
      <div className="p-3 text-sm text-gray-500 text-center">
        No content returned
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {content.map((item, index) => (
        <ContentItem key={index} item={item} index={index} />
      ))}
    </div>
  );
};

const ActionButtons: React.FC<{ result: any }> = ({ result }) => {
  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
  };

  return (
    <div className="flex items-center space-x-2 pt-2 border-t border-gray-200">
      <button 
        onClick={copyToClipboard}
        className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700"
      >
        <Copy className="w-3 h-3" />
        <span>Copy</span>
      </button>
      {result.tool_name && (
        <button className="flex items-center space-x-1 text-xs text-gray-500 hover:text-gray-700">
          <ExternalLink className="w-3 h-3" />
          <span>Tool Info</span>
        </button>
      )}
    </div>
  );
};

// ============================================
// Main Component
// ============================================

export const MCPResultCard: React.FC<MCPResultCardProps> = ({
  result,
  execution,
  show_raw_data = false,
  collapsible = true,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(!collapsible);
  const [showRaw, setShowRaw] = useState(show_raw_data);

  const toggleExpanded = () => setIsExpanded(!isExpanded);
  const toggleRaw = () => setShowRaw(!showRaw);

  const cardClassName = useMemo(() => {
    return `mcp-result-card border rounded-lg ${getStatusColor(result.is_error)} ${className}`;
  }, [result.is_error, className]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cardClassName}
    >
      {collapsible ? (
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger className="w-full">
            <div className="flex items-center justify-between p-3">
              <div className="flex items-center space-x-2">
                {getStatusIcon(result.is_error)}
                <span className="font-medium text-sm">{result.tool_name}</span>
                <span className="text-xs text-gray-500">@{result.server_name}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-500">{formatDuration(result.execution_time_ms)}</span>
                {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              </div>
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border-t border-gray-200">
              {result.is_error ? (
                <ErrorDisplay errorMessage={result.error_message || 'Unknown error'} />
              ) : (
                <ContentDisplay content={result.content} />
              )}
              <div className="p-3">
                <ActionButtons result={result} />
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
      ) : (
        <>
          <ResultHeader result={result} execution={execution} />
          {result.is_error ? (
            <ErrorDisplay errorMessage={result.error_message || 'Unknown error'} />
          ) : (
            <ContentDisplay content={result.content} />
          )}
          <div className="p-3">
            <ActionButtons result={result} />
          </div>
        </>
      )}

      {showRaw && (
        <div className="border-t border-gray-200 p-3 bg-gray-50">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Code className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Raw Data</span>
            </div>
            <button 
              onClick={toggleRaw}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Hide
            </button>
          </div>
          <RawJsonView data={result} />
        </div>
      )}
    </motion.div>
  );
};

MCPResultCard.displayName = 'MCPResultCard';