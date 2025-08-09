import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { examplePrompts } from '@/lib/examplePrompts';
import { useChatStore } from '@/store';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';

export const ExamplePrompts: React.FC = () => {
  const { sendMessage } = useWebSocket();
  const { setProcessing } = useChatStore();
  const [isOpen, setIsOpen] = React.useState(true);

  const handlePromptClick = (prompt: string) => {
    sendMessage(JSON.stringify({ type: 'user_message', payload: { text: prompt } }));
    setProcessing(true);
    setIsOpen(false); // Collapse the panel after sending a prompt
  };

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 rounded-t-lg">
        <h2 className="text-lg font-semibold">Example Prompts</h2>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm">
            {isOpen ? "Hide" : "Show"}
          </Button>
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent className="p-4 bg-gray-50 rounded-b-lg">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {examplePrompts.map((prompt, index) => (
            <Card key={index} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => handlePromptClick(prompt)}>
              <CardHeader>
                <CardTitle className="text-base font-medium">Example {index + 1}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 line-clamp-3">{prompt}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
};
