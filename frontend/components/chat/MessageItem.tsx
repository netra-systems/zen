
import React, { useMemo, useCallback } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';
import { MCPToolIndicator } from './MCPToolIndicator';
import { motion } from 'framer-motion';
import { AlertCircle, Bot, ChevronDown, ChevronRight, Clock, Code, FileText, User, Wrench } from 'lucide-react';
import { getMessageDisplayName, shouldShowSubtitle, getMessageSubtitle } from '@/utils/message-display';

// ============================================
// Helper Functions (8 lines max each)
// ============================================

const createDefaultTimeString = (): string => {
  return new Date().toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
};

const parseCreatedAtDate = (created_at: string | number | undefined): Date | null => {
  if (!created_at) return null;
  const date = new Date(created_at);
  return isNaN(date.getTime()) ? null : date;
};

const formatMessageTimestamp = (created_at: string | number | undefined): string => {
  const date = parseCreatedAtDate(created_at);
  if (!date) return createDefaultTimeString();
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit'
  });
};

const renderErrorContent = (error: string) => (
  <div className="flex items-start space-x-2 p-3 bg-red-50 rounded-lg border border-red-200">
    <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
    <p className="text-red-700 text-sm">{error}</p>
  </div>
);

const renderToolContent = (
  tool_info: any,
  isToolExpanded: boolean,
  toggleToolExpanded: () => void
) => (
  <div className="space-y-3">
    <Collapsible open={isToolExpanded} onOpenChange={toggleToolExpanded}>
      {renderToolTrigger(isToolExpanded)}
      {renderToolCollapsibleContent(tool_info)}
    </Collapsible>
  </div>
);

const renderToolTrigger = (isToolExpanded: boolean) => (
  <CollapsibleTrigger className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-medium text-sm">
    {isToolExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
    <Code className="w-4 h-4" />
    <span>Tool Information</span>
  </CollapsibleTrigger>
);

const renderToolCollapsibleContent = (tool_info: any) => (
  <CollapsibleContent className="mt-3">
    <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
      <RawJsonView data={tool_info} />
    </div>
  </CollapsibleContent>
);

const renderRegularContent = (
  content: string | any,
  type: string,
  references: string[] | undefined,
  id: string | undefined
) => {
  const textContent = typeof content === 'string' 
    ? content 
    : (content?.text || JSON.stringify(content));
  return (
    <div className="space-y-3">
      <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{textContent}</p>
      {type === 'user' && references && references.length > 0 && 
        renderUserReferences(references, id)
      }
    </div>
  );
};

const renderUserReferences = (references: string[], id: string | undefined) => (
  <div className="mt-4 p-3 glass-light rounded-lg border border-emerald-200">
    {renderReferencesHeader()}
    {renderReferencesList(references, id)}
  </div>
);

const renderReferencesHeader = () => (
  <div className="flex items-center space-x-2 mb-2">
    <FileText className="w-4 h-4 text-emerald-600" />
    <span className="font-semibold text-sm text-emerald-800">References</span>
  </div>
);

const renderReferencesList = (references: string[], id: string | undefined) => (
  <ul className="space-y-1">
    {references.map((ref, index) => (
      <li key={`${id}-ref-${index}-${ref.substring(0, 20)}`} className="text-sm text-emerald-700 flex items-start">
        <span className="mr-2 text-blue-500">•</span>
        <span>{ref}</span>
      </li>
    ))}
  </ul>
);

const renderMCPIndicator = (mcpExecutions: any[] | undefined) => {
  if (!mcpExecutions || mcpExecutions.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <MCPToolIndicator 
        tool_executions={mcpExecutions}
        server_status="CONNECTED"
        show_details={true}
      />
    </div>
  );
};

interface MessageProps {
  message: MessageType;
}

export const MessageItem: React.FC<MessageProps> = React.memo(({ message }) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references, error, created_at, id } = message;
  const [isToolExpanded, setIsToolExpanded] = React.useState(false);
  const [isRawExpanded, setIsRawExpanded] = React.useState(false);

  const formattedTimestamp = useMemo(() => {
    return formatMessageTimestamp(created_at);
  }, [created_at]);

  const toggleToolExpanded = useCallback(() => {
    setIsToolExpanded(prev => !prev);
  }, []);

  const toggleRawExpanded = useCallback(() => {
    setIsRawExpanded(prev => !prev);
  }, []);

  const messageIcon = useMemo(() => {
    switch (type) {
      case 'user':
        return <User className="w-4 h-4" />;
      case 'tool':
        return <Wrench className="w-4 h-4" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Bot className="w-4 h-4" />;
    }
  }, [type]);

  const renderContent = () => {
    if (error) return renderErrorContent(error);
    if (tool_info) return renderToolContent(tool_info, isToolExpanded, toggleToolExpanded);
    return renderRegularContent(content, type, references, id);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`mb-4 flex ${type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <Card className={`w-full max-w-3xl shadow-sm hover:shadow-md transition-shadow duration-200 ${
        type === 'user' 
          ? 'bg-white/95 backdrop-blur-sm border-emerald-200' 
          : type === 'error'
          ? 'bg-red-50 border-red-200'
          : 'bg-white border-gray-200'
      }`}>
        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <Avatar className="w-9 h-9 border-2 border-white shadow-sm">
                <AvatarFallback className={`font-bold text-sm ${
                  type === 'user' ? 'bg-emerald-500 text-white' : 'bg-gradient-to-r from-purple-600 to-pink-600 text-white'
                }`}>
                  {type === 'user' ? 'U' : 'AI'}
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center space-x-2">
                  {messageIcon}
                  <CardTitle className="text-base font-semibold text-gray-900">
                    {getMessageDisplayName(type, sub_agent_name)}
                  </CardTitle>
                </div>
                {shouldShowSubtitle(type, sub_agent_name) && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    {getMessageSubtitle(type, sub_agent_name)}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formattedTimestamp}</span>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="px-5 pb-4">
          {renderContent()}
          
          {raw_data && (
            <Collapsible open={isRawExpanded} onOpenChange={toggleRawExpanded} className="mt-4">
              <CollapsibleTrigger className="flex items-center space-x-2 text-xs text-gray-500 hover:text-gray-700 transition-colors">
                {isRawExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                <Code className="w-3 h-3" />
                <span>Raw Data</span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div className="bg-gray-50 rounded-md p-3 border border-gray-200">
                  <RawJsonView data={raw_data} />
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
          
          {renderMCPIndicator(message.metadata?.mcpExecutions)}
          
          {id && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400">Message ID: {id}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
});

MessageItem.displayName = 'MessageItem';
