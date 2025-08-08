import { v4 as uuidv4 } from 'uuid';
import { AgentState, AgentListener, Reference, ToolCallChunk, ToolCall, ServerEvent } from '@/types';

class Agent {
    private state: AgentState = {
        messages: [],
        isThinking: false,
        error: null,
        toolArgBuffers: {},
    };
    private listeners: AgentListener[] = [];

    subscribe(listener: AgentListener) {
        this.listeners.push(listener);
        listener(this.state);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }

    private notifyState() {
        this.listeners.forEach(listener => listener(this.state));
    }

    private setState(updater: (prevState: AgentState) => AgentState) {
        this.state = updater(this.state);
        this.notifyState();
    }

    start(message: string, sendMessage: (message: any) => void, references?: Reference[]) {
        this.setState(prev => ({
            ...prev,
            isThinking: true,
            messages: [...prev.messages, { id: uuidv4(), role: 'user', type: 'user', content: message, references }],
        }));

        const streamInput = {
            input: message,
            agent_id: "apex_optimizer_agent_v2",
            references: references,
            enable_update_step_results: true,
        };

        sendMessage(streamInput);
    }

    stop(sendMessage: (message: any) => void) {
        if (this.state.isThinking) {
            sendMessage({ type: 'stop' });
            this.setState(prev => ({ ...prev, isThinking: false }));
        }
    }

    handleWebSocketMessage = (serverEvent: ServerEvent) => {
        try {
            const { event: eventName, data, run_id } = serverEvent;

            this.setState(prev => {
                const newMessages = [...prev.messages];
                let isThinking = prev.isThinking;
                const toolArgBuffers = { ...prev.toolArgBuffers };

                const lastMessage = newMessages[newMessages.length - 1];

                switch (eventName) {
                    case 'stream_start':
                        isThinking = true;
                        newMessages.push({
                            id: run_id,
                            role: 'assistant',
                            type: 'agent',
                            subAgentName: 'ApexOptimizerAgent',
                            content: '',
                            tools: [],
                            todos: [],
                            toolErrors: [],
                            rawServerEvent: serverEvent,
                        });
                        break;

                    case 'stream_end':
                        isThinking = false;
                        break;

                    case 'text_chunk':
                        if (lastMessage?.type === 'agent') {
                            lastMessage.content += data.chunk;
                        }
                        break;

                    case 'tool_code_chunk':
                        if (lastMessage?.type === 'agent') {
                            const { tool_name, code_chunk } = data;
                            const toolIndex = lastMessage.tools.findIndex(t => t.name === tool_name);
                            if (toolIndex !== -1) {
                                lastMessage.tools[toolIndex].input += code_chunk;
                            } else {
                                lastMessage.tools.push({ name: tool_name, input: code_chunk, output: null });
                            }
                        }
                        break;
                    
                    case 'tool_call_chunk':
                        if (lastMessage?.type === 'agent') {
                            const chunk = data.chunk as ToolCallChunk;
                            if (chunk.name && chunk.id) {
                                const toolIndex = lastMessage.tools.findIndex(t => t.id === chunk.id);
                                if (toolIndex === -1) {
                                    lastMessage.tools.push({
                                        id: chunk.id,
                                        name: chunk.name,
                                        input: chunk.args,
                                        output: null
                                    });
                                    toolArgBuffers[chunk.id] = chunk.args || "";
                                } else {
                                    toolArgBuffers[chunk.id] += chunk.args || "";
                                    try {
                                        lastMessage.tools[toolIndex].input = JSON.parse(toolArgBuffers[chunk.id]);
                                    } catch (err) {
                                        // Invalid JSON, wait for more chunks
                                    }
                                }
                            }
                        }
                        break;
                    
                    case 'tool_call':
                        if (lastMessage?.type === 'agent') {
                            const toolCall = data.chunk as ToolCall;
                            if (toolCall.name && toolCall.id) {
                                const toolIndex = lastMessage.tools.findIndex(t => t.id === toolCall.id);
                                if (toolIndex === -1) {
                                    lastMessage.tools.push({
                                        id: toolCall.id,
                                        name: toolCall.name,
                                        input: toolCall.args,
                                        output: null
                                    });
                                } else {
                                    lastMessage.tools[toolIndex].input = toolCall.args;
                                }
                            }
                        }
                        break;

                    case 'tool_output':
                        if (lastMessage?.type === 'agent') {
                            const { tool_name, tool_output } = data;
                            const tool = lastMessage.tools.find(t => t.name === tool_name);
                            if (tool) {
                                tool.output = tool_output;
                            }
                        }
                        break;

                    case 'todo_list_update':
                        if (lastMessage?.type === 'agent') {
                            lastMessage.todos = data.map((todo: { description: string; state: 'pending' | 'done' | 'error' }) => ({
                                description: todo.description,
                                state: todo.state,
                            }));
                        }
                        break;

                    case 'error':
                        isThinking = false;
                        const errorContent = data.error?.message || JSON.stringify(data);
                        newMessages.push({
                            id: uuidv4(),
                            role: 'assistant',
                            type: 'error',
                            content: `An error occurred: ${errorContent}`,
                            isError: true,
                            rawServerEvent: serverEvent,
                        });

                        break;

                    default:
                        // Handle other events or ignore
                        break;
                }

                return { ...prev, messages: newMessages, isThinking, toolArgBuffers };
            });

        } catch (error) {
            console.error("Error handling WebSocket message:", error);
            this.setState(prev => ({
                ...prev,
                isThinking: false,
                error: new Error("Failed to process server event."),
            }));
        }
    };
}

export const agent = new Agent();