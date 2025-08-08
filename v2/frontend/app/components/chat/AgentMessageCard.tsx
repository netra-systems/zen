
import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { AgentMessage, Tool, Todo } from '@/app/types/index';
import JsonTreeView from './JsonTreeView';

interface AgentMessageCardProps {
    message: AgentMessage;
}

const ToolDisplay: React.FC<{ tool: Tool }> = ({ tool }) => (
    <div className="tool-display mb-4 p-4 rounded-lg bg-gray-100 dark:bg-gray-800">
        <p className="font-semibold text-lg text-gray-800 dark:text-gray-200">{tool.name}</p>
        <div className="mt-2">
            <h4 className="font-medium text-md text-gray-600 dark:text-gray-400">Input:</h4>
            <JsonTreeView data={tool.input} />
        </div>
        {tool.output && (
            <div className="mt-2">
                <h4 className="font-medium text-md text-gray-600 dark:text-gray-400">Output:</h4>
                <JsonTreeView data={tool.output} />
            </div>
        )}
    </div>
);

const TodoList: React.FC<{ todos: Todo[] }> = ({ todos }) => (
    <ul className="list-disc pl-5">
        {todos.map((todo, index) => (
            <li key={index} className={`text-sm ${todo.state === 'completed' ? 'line-through text-gray-500' : 'text-gray-800 dark:text-gray-200'}`}>
                {todo.description}
            </li>
        ))}
    </ul>
);

export const AgentMessageCard: React.FC<AgentMessageCardProps> = ({ message }) => {
    const toolsInUse = message.tools.filter(tool => !tool.output);
    const completedTools = message.tools.filter(tool => tool.output);

    return (
        <Card className="w-full border-2 border-gray-200 dark:border-gray-700 rounded-xl shadow-lg">
            <CardHeader className="bg-gray-50 dark:bg-gray-800 rounded-t-xl p-6">
                <CardTitle className="text-2xl font-bold text-gray-800 dark:text-gray-200">{message.subAgentName}</CardTitle>
                {toolsInUse.length > 0 && (
                    <div className="text-md text-gray-500 dark:text-gray-400 mt-2">
                        <strong>Tools in use:</strong> {toolsInUse.map(tool => tool.name).join(', ')}
                    </div>
                )}
            </CardHeader>
            <CardContent className="p-6">
                {message.content && <p className="text-md text-gray-700 dark:text-gray-300 mb-6">{message.content}</p>}
                
                {completedTools.length > 0 && (
                    <div className="mb-6">
                        <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">Tools Used</h3>
                        {completedTools.map((tool, index) => (
                            <ToolDisplay key={index} tool={tool} />
                        ))}
                    </div>
                )}

                {message.toolErrors.length > 0 && (
                    <div className="p-4 rounded-lg bg-red-100 dark:bg-red-900">
                        <h4 className="font-semibold text-lg text-red-700 dark:text-red-300 mb-2">Tool Errors:</h4>
                        <ul className="list-disc pl-5 text-red-600 dark:text-red-400">
                            {message.toolErrors.map((error, index) => (
                                <li key={index}>{error}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </CardContent>
            {message.todos.length > 0 && (
                <CardFooter className="bg-gray-50 dark:bg-gray-800 rounded-b-xl p-6">
                    <Accordion type="single" collapsible className="w-full">
                        <AccordionItem value="item-1">
                            <AccordionTrigger className="text-lg font-semibold text-gray-800 dark:text-gray-200">TODO List</AccordionTrigger>
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
