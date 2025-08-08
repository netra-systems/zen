
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { AgentMessage, Tool, Todo } from '@/app/types/index';
import JsonTreeView from './JsonTreeView';

interface AgentMessageCardProps {
    message: AgentMessage;
}

const ToolDisplay: React.FC<{ tool: Tool }> = ({ tool }) => (
    <div className="tool-display">
        <p className="font-semibold">{tool.name}</p>
        <JsonTreeView data={tool.input} />
        {tool.output && <JsonTreeView data={tool.output} />}
    </div>
);

const TodoList: React.FC<{ todos: Todo[] }> = ({ todos }) => (
    <ul className="list-disc pl-5">
        {todos.map((todo, index) => (
            <li key={index} className={`${todo.state === 'completed' ? 'line-through' : ''}`}>
                {todo.description}
            </li>
        ))}
    </ul>
);

export const AgentMessageCard: React.FC<AgentMessageCardProps> = ({ message }) => {
    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle className="text-lg">{message.subAgentName}</CardTitle>
            </CardHeader>
            <CardContent>
                {message.content && <p className="text-muted-foreground">{message.content}</p>}
                {message.tools.length > 0 &&
                    <div className="mt-4">
                        <h4 className="font-semibold">Tools Used:</h4>
                        {message.tools.map((tool, index) => (
                            <ToolDisplay key={index} tool={tool} />
                        ))}
                    </div>
                }
                {message.toolErrors.length > 0 && (
                    <div className="mt-4">
                        <h4 className="font-semibold text-red-500">Tool Errors:</h4>
                        <ul className="list-disc pl-5 text-red-500">
                            {message.toolErrors.map((error, index) => (
                                <li key={index}>{error}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </CardContent>
            {message.todos.length > 0 && (
                <CardFooter>
                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger>TODO List</AccordionTrigger>
                            <AccordionContent>
                                <TodoList todos={message.todos} />
                            </AccordionContent>
                        </AccordionItem>
                    </Accordion>
                </CardFooter>
            )}
        </Card>
    );
};
