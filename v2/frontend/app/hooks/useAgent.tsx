
import { getToken, getUserId } from '../lib/user';
import { useEffect, useRef, useState } from 'react';
import { Message, ToolCall, ToolOutput, StateUpdate, EventName } from '../types/chat';
import { produce } from 'immer';

export function useAgent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [showThinking, setShowThinking] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const runIdRef = useRef<string | null>(null);

  const addMessage = (message: Message) => {
    setMessages(
      produce(draft => {
        const existingMessageIndex = draft.findIndex(m => m.id === message.id);
        if (existingMessageIndex !== -1) {
          draft[existingMessageIndex] = message;
        } else {
          draft.push(message);
        }
      })
    );
  };

  useEffect(() => {
    const connect = async () => {
      const token = await getToken();
      if (token) {
        const runId = `run_${Date.now()}`;
        runIdRef.current = runId;
        const ws = new WebSocket(`ws://localhost:8000/agent/${runId}?token=${token}`);
        
        ws.onopen = () => {
          console.log('WebSocket connected');
          setIsConnected(true);
          ws.send(JSON.stringify({ type: 'handshake', message: 'Hello from client' }));
        };

        ws.onmessage = (event) => {
          const message = JSON.parse(event.data);
          console.log('Received message:', message);

          const { event: eventName, data, run_id } = message;

          if (eventName === 'run_complete') {
            setShowThinking(false);
            return;
          }

          setMessages(produce(draft => {
            let existingMessage = draft.find(m => m.id === run_id) as ArtifactMessage | undefined;

            if (!existingMessage || existingMessage.type !== 'artifact') {
                const newMessage: Message = {
                    id: run_id || `msg_${Date.now()}`,
                    role: 'agent',
                    timestamp: new Date().toISOString(),
                    type: 'artifact',
                    name: eventName as EventName,
                    data: data,
                };
                draft.push(newMessage);
                existingMessage = newMessage as ArtifactMessage;
            } else {
                existingMessage.name = eventName as EventName;
                existingMessage.data = data;
            }
            
            let content: string | undefined;
            if (data?.chunk?.agent?.messages?.[0]?.content) {
              content = data.chunk.agent.messages[0].content;
            } else if (data?.output?.messages?.[0]?.content) {
              content = data.output.messages[0].content;
            } else if (data?.chunk?.messages?.[0]?.content) {
              content = data.chunk.messages[0].content;
            } else if (typeof data?.chunk?.content === 'string') {
              content = data.chunk.content;
            }
            if (content) {
                existingMessage.content = (existingMessage.content || '') + content;
            }
  
            let tool_calls: ToolCall[] | undefined;
            if (data?.tool_calls) {
              tool_calls = data.tool_calls;
            } else if (data?.output?.messages?.[0]?.tool_calls) {
              tool_calls = data.output.messages[0].tool_calls;
            } else if (data?.chunk?.tool_calls) {
              tool_calls = data.chunk.tool_calls;
            } else if (data?.chunk?.agent?.messages?.[0]?.tool_calls) {
              tool_calls = data.chunk.agent.messages[0].tool_calls;
            }
            if (tool_calls) {
                existingMessage.tool_calls = [...(existingMessage.tool_calls || []), ...tool_calls];
            }
  
            if (data?.tool_outputs) {
                existingMessage.tool_outputs = [...(existingMessage.tool_outputs || []), ...data.tool_outputs];
            }
  
            const updateStateCall = tool_calls?.find(tc => tc.name === 'update_state');
            if (updateStateCall?.args) {
              const newCompletedStep = updateStateCall.args.completed_step as string;
              const existingSteps = existingMessage.state_updates?.completed_steps || [];
              existingMessage.state_updates = {
                todo_list: updateStateCall.args.todo_list as string[],
                completed_steps: newCompletedStep ? [...existingSteps, newCompletedStep] : existingSteps,
              };
            } else if (data?.input?.todo_list) {
                existingMessage.state_updates = {
                    todo_list: data.input.todo_list,
                    completed_steps: data.input.completed_steps || [],
                };
            }
          }));
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setIsConnected(false);
          setShowThinking(false);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setError(new Error('WebSocket error'));
          setShowThinking(false);
        };

        setSocket(ws);
      }
    };

    connect();

    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);

  const startAgent = async (message: string) => {
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      timestamp: new Date().toISOString(),
      type: 'text',
      content: message,
    };
    setMessages(prev => [...prev, userMessage]);

    if (socket && isConnected) {
      setShowThinking(true);
      const thinkingMessage: Message = {
        id: runIdRef.current!,
        role: 'agent',
        timestamp: new Date().toISOString(),
        type: 'thinking',
      };
      addMessage(thinkingMessage);

      try {
        const userId = getUserId();
        if (!userId) {
          console.error('User ID not found');
          return;
        }
        const analysisRequest = {
          settings: {
            debug_mode: false,
          },
          request: {
            id: runIdRef.current,
            user_id: userId,
            query: message,
            workloads: [],
          },
        };
        socket.send(JSON.stringify({ action: 'start_agent', payload: analysisRequest }));
      } catch (error) {
        console.error('Error sending message:', error);
        setError(error as Error);
        setShowThinking(false);
      }
    }
  };

  return { startAgent, messages, showThinking, error };
}
