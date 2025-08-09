
import React, { useEffect, useRef } from 'react';
import { Message as MessageType } from '@/types/chat';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { RawJsonView } from './RawJsonView';
import { motion } from 'framer-motion';

interface MessageProps {
  message: MessageType;
}

export const MessageItem: React.FC<MessageProps> = ({ message }) => {
  const { type, content, sub_agent_name, tool_info, raw_data, references, error } = message;

  const renderContent = () => {
    if (error) {
      return <p className="text-red-500">{error}</p>;
    }
    if (tool_info) {
      return (
        <Collapsible>
          <CollapsibleTrigger className="text-blue-500 font-semibold">View Tool Info</CollapsibleTrigger>
          <CollapsibleContent className="mt-2">
            <RawJsonView data={tool_info} />
          </CollapsibleContent>
        </Collapsible>
      );
    }
    return (
      <>
        <p className="text-gray-800">{content}</p>
        {type === 'user' && references && references.length > 0 && (
          <div className="mt-4 text-sm text-gray-600">
            <strong className="font-semibold">References:</strong>
            <ul className="list-disc list-inside mt-1">
              {references.map((ref, index) => (
                <li key={index}>{ref}</li>
              ))}
            </ul>
          </div>
        )}
      </>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className={`mb-6 flex items-start ${type === 'user' ? 'justify-end' : ''}`}>
      <Card className={`w-full max-w-2xl shadow-md ${type === 'user' ? 'bg-blue-100' : 'bg-white'}`}>
        <CardHeader className="pb-2">
          <div className="flex items-center">
            <Avatar className="mr-4">
              <AvatarImage src={type === 'user' ? '' : '/bot.png'} />
              <AvatarFallback className="font-bold">{type === 'user' ? 'U' : 'A'}</AvatarFallback>
            </Avatar>
            <CardTitle className="text-lg font-bold text-gray-900">{sub_agent_name || (type === 'user' ? 'You' : 'Agent')}</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          {renderContent()}
          {raw_data && (
            <Collapsible className="mt-4">
              <CollapsibleTrigger className="text-xs text-gray-500 hover:text-gray-700">View Raw Data</CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <RawJsonView data={raw_data} />
              </CollapsibleContent>
            </Collapsible>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
};
