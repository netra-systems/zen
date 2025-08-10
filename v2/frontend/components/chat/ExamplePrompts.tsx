import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { examplePrompts } from '@/lib/examplePrompts';
import { useChatStore } from '@/store/chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { ChevronDown, Send } from 'lucide-react';
import { motion } from 'framer-motion';
import { Message } from '@/types/chat';

export const ExamplePrompts: React.FC = () => {
  const { sendMessage } = useWebSocket();
  const { setProcessing, addMessage } = useChatStore();
  const [isOpen, setIsOpen] = React.useState(true);

  const handlePromptClick = (prompt: string) => {
    // Add user message to chat immediately
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
      displayed_to_user: true
    };
    addMessage(userMessage);
    
    // Send message via WebSocket
    sendMessage({ type: 'user_message', payload: { text: prompt, references: [] } });
    setProcessing(true);
    setIsOpen(false); // Collapse the panel after sending a prompt
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full bg-gray-50 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-700">Example Prompts</h2>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="flex items-center">
            <span className="mr-2">{isOpen ? 'Hide' : 'Show'}</span>
            <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="mt-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {examplePrompts.map((prompt, index) => (
            <motion.div
              key={index}
              whileHover={{ scale: 1.03 }}
              transition={{ type: 'spring', stiffness: 300 }}
            >
              <Card
                className="cursor-pointer h-full flex flex-col justify-between bg-white shadow-md hover:shadow-lg transition-shadow rounded-lg overflow-hidden"
                onClick={() => handlePromptClick(prompt)}
              >
                <CardContent className="p-4">
                  <p className="text-sm text-gray-700">{prompt}</p>
                </CardContent>
                <div className="p-2 bg-gray-100 flex justify-end">
                  <Send className="w-4 h-4 text-blue-500" />
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};