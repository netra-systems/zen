import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { examplePrompts } from '@/lib/examplePrompts';
import { generateUniqueId } from '@/lib/utils';
import { useUnifiedChatStore } from '@/store/unified-chat';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useAuthStore } from '@/store/authStore';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { ChevronDown, Send, Sparkles, Zap, TrendingUp, Shield, Database, Brain } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { logger } from '@/utils/debug-logger';

export const ExamplePrompts: React.FC = () => {
  const { sendMessage } = useWebSocket();
  const { setProcessing, addMessage } = useUnifiedChatStore();
  const { isAuthenticated } = useAuthStore();
  const [isOpen, setIsOpen] = React.useState(true);

  const handlePromptClick = (prompt: string) => {
    // Check if user is authenticated
    if (!isAuthenticated) {
      logger.error('User must be authenticated to send messages');
      return;
    }
    
    // Provide immediate feedback that the prompt was clicked
    logger.info('Starting new conversation with prompt:', prompt);
    
    // Add user message to chat immediately
    const userMessage = {
      id: generateUniqueId('msg'),
      role: 'user' as const,
      content: prompt,
      timestamp: Date.now()
    };
    addMessage(userMessage);
    
    // Send start_agent message for example prompts (these start new conversations)
    sendMessage({ 
      type: 'start_agent', 
      payload: { 
        user_request: prompt,
        thread_id: null,
        context: { source: 'example_prompt' },
        settings: {}
      } 
    });
    setProcessing(true);
    setIsOpen(false); // Collapse the panel after sending a prompt
  };

  const getPromptIcon = (index: number) => {
    const icons = [
      <TrendingUp key="trending" className="w-5 h-5" />,
      <Brain key="brain" className="w-5 h-5" />,
      <Zap key="zap" className="w-5 h-5" />,
      <Shield key="shield" className="w-5 h-5" />,
      <Database key="database" className="w-5 h-5" />,
      <Sparkles key="sparkles" className="w-5 h-5" />
    ];
    return icons[index % icons.length];
  };

  const getCardGradient = (index: number) => {
    const gradients = [
      'from-emerald-50 to-emerald-100 hover:from-emerald-100 hover:to-emerald-200',
      'from-purple-50 to-purple-100 hover:from-purple-100 hover:to-purple-200',
      'from-zinc-50 to-zinc-100 hover:from-zinc-100 hover:to-zinc-200',
      'from-amber-50 to-amber-100 hover:from-amber-100 hover:to-amber-200',
      'from-emerald-50 to-teal-100 hover:from-emerald-100 hover:to-teal-200',
      'from-purple-50 to-pink-100 hover:from-purple-100 hover:to-pink-200'
    ];
    return gradients[index % gradients.length];
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full px-6 py-6" style={{
      background: 'linear-gradient(180deg, rgba(250, 250, 250, 0.95) 0%, rgba(255, 255, 255, 0.98) 100%)',
      backdropFilter: 'blur(8px)'
    }}>
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between mb-4"
      >
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-emerald-500" />
          <h2 className="text-xl font-bold bg-gradient-to-r from-emerald-600 to-emerald-700 bg-clip-text text-transparent">
            Quick Start Examples
          </h2>
        </div>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="flex items-center hover:bg-gray-100 rounded-lg">
            <span className="mr-2 text-sm font-medium">{isOpen ? 'Hide' : 'Show'}</span>
            <motion.div
              animate={{ rotate: isOpen ? 180 : 0 }}
              transition={{ duration: 0.3 }}
            >
              <ChevronDown className="w-4 h-4" />
            </motion.div>
          </Button>
        </CollapsibleTrigger>
      </motion.div>
      
      <AnimatePresence>
        {isOpen && (
          <CollapsibleContent forceMount>
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
            >
              {examplePrompts.map((prompt, index) => (
                <motion.div
                  key={generateUniqueId('prompt')}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  whileHover={{ y: -4, scale: 1.02, transition: { duration: 0.2 } }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Card
                    className={`cursor-pointer h-full group relative overflow-hidden border-0 shadow-md hover:shadow-xl transition-all duration-300 bg-gradient-to-br ${getCardGradient(index)}`}
                    onClick={() => handlePromptClick(prompt)}
                  >
                    <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity duration-300" />
                    
                    <CardContent className="p-5 flex flex-col h-full">
                      <div className="flex items-start justify-between mb-3">
                        <div className={`p-2 rounded-lg bg-white/80 shadow-sm text-${['blue', 'purple', 'green', 'orange', 'cyan', 'yellow'][index % 6]}-600`}>
                          {getPromptIcon(index)}
                        </div>
                        <motion.div
                          className="opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                          whileHover={{ scale: 1.1 }}
                        >
                          <Send className="w-4 h-4 text-gray-600" />
                        </motion.div>
                      </div>
                      
                      <p className="text-sm text-gray-700 font-medium leading-relaxed flex-grow">
                        {prompt}
                      </p>
                      
                      <div className="mt-3 pt-3 border-t border-gray-200/50">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500 flex items-center">
                            <span className="mr-1">Click to start conversation</span>
                            <motion.span
                              animate={{ x: [0, 2, 0] }}
                              transition={{ duration: 1, repeat: Infinity }}
                            >
                              →
                            </motion.span>
                          </span>
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">
                            New Thread
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </CollapsibleContent>
        )}
      </AnimatePresence>
    </Collapsible>
  );
};