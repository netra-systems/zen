
import React from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';
import { motion } from 'framer-motion';
import { AlertCircle, Bot, ChevronDown, ChevronRight, Clock, Code, FileText, User, Wrench } from 'lucide-react';

interface MessageProps {
  message: MessageType;
}

export const MessageItem: React.FC<MessageProps> = ({ message }) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references, error, created_at, id } = message;
  const [isToolExpanded, setIsToolExpanded] = React.useState(false);
  const [isRawExpanded, setIsRawExpanded] = React.useState(false);

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) {
      return new Date().toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    }
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return new Date().toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    }
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getMessageIcon = () => {
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
  };

  const renderContent = () => {
    if (error) {
      return (
        <div className="flex items-start space-x-2 p-3 bg-red-50 rounded-lg border border-red-200">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
          <p className="text-red-700 text-sm">{error}</p>
        </div>
      );
    }
    
    if (tool_info) {
      return (
        <div className="space-y-3">
          <Collapsible open={isToolExpanded} onOpenChange={setIsToolExpanded}>
            <CollapsibleTrigger className="flex items-center space-x-2 text-blue-600 hover:text-blue-700 font-medium text-sm">
              {isToolExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
              <Code className="w-4 h-4" />
              <span>Tool Information</span>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-3">
              <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                <RawJsonView data={tool_info} />
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      );
    }
    
    return (
      <div className="space-y-3">
        <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">{content}</p>
        
        {type === 'user' && references && references.length > 0 && (
          <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center space-x-2 mb-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <span className="font-semibold text-sm text-blue-800">References</span>
            </div>
            <ul className="space-y-1">
              {references.map((ref, index) => (
                <li key={index} className="text-sm text-blue-700 flex items-start">
                  <span className="mr-2 text-blue-500">•</span>
                  <span>{ref}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`mb-4 flex ${type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <Card className={`w-full max-w-3xl shadow-sm hover:shadow-md transition-shadow duration-200 ${
        type === 'user' 
          ? 'bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200' 
          : type === 'error'
          ? 'bg-red-50 border-red-200'
          : 'bg-white border-gray-200'
      }`}>
        <CardHeader className="pb-3 pt-4 px-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-3">
              <Avatar className="w-9 h-9 border-2 border-white shadow-sm">
                <AvatarFallback className={`font-bold text-sm ${
                  type === 'user' ? 'bg-blue-500 text-white' : 'bg-gradient-to-r from-blue-600 to-purple-600 text-white'
                }`}>
                  {type === 'user' ? 'U' : 'AI'}
                </AvatarFallback>
              </Avatar>
              <div>
                <div className="flex items-center space-x-2">
                  {getMessageIcon()}
                  <CardTitle className="text-base font-semibold text-gray-900">
                    {sub_agent_name || (type === 'user' ? 'You' : 'Netra Agent')}
                  </CardTitle>
                </div>
                {type !== 'user' && sub_agent_name && (
                  <p className="text-xs text-gray-500 mt-0.5">
                    {type === 'tool' ? 'Tool Execution' : 'Agent Response'}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <Clock className="w-3 h-3" />
              <span>{formatTimestamp(created_at)}</span>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="px-5 pb-4">
          {renderContent()}
          
          {raw_data && (
            <Collapsible open={isRawExpanded} onOpenChange={setIsRawExpanded} className="mt-4">
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
          
          {id && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400">Message ID: {id}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};
