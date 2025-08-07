import { getToken, getUserId } from '../lib/user';
import { useEffect, useRef, useState } from 'react';
import { Message, StreamEvent, ArtifactMessage, EventName } from '../types/chat';
import { produce } from 'immer';

const processStreamEvent = (draft: Message[], event: StreamEvent) => {
  const { event: eventName, data, run_id } = event;

  let existingMessage = draft.find(m => m.id === run_id) as ArtifactMessage | undefined;

  if (!existingMessage || existingMessage.type !== 'artifact') {
    const newMessage: ArtifactMessage = {
      id: run_id || `msg_${Date.now()}`,
      role: 'agent',
      timestamp: new Date().toISOString(),
      type: 'artifact',
      name: eventName,
      data: data,
      tool_calls: [],
      tool_outputs: [],
      state_updates: { todo_list: [], completed_steps: [] },
    };
    draft.push(newMessage);
    existingMessage = newMessage;
  } else {
    existingMessage.name = eventName;
    existingMessage.data = data;
  }

  switch (eventName) {
    case 'on_chain_start':
      if ('input' in data && data.input?.todo_list) {
        existingMessage.state_updates = {
          todo_list: data.input.todo_list,
          completed_steps: data.input.completed_steps || [],
        };
      }
      break;

    case 'on_chat_model_stream':
      if ('chunk' in data) {
        if (data.chunk?.content) {
          existingMessage.content = (existingMessage.content || '') + data.chunk.content;
        }
        if (data.chunk?.tool_calls) {
          existingMessage.tool_calls = [...(existingMessage.tool_calls || []), ...data.chunk.tool_calls];
        }
      }
      break;

    case 'on_tool_end':
      if ('output' in data) {
        const toolOutput = {
          tool_call_id: run_id, // This might need adjustment based on actual data
          content: typeof data.output === 'string' ? data.output : JSON.stringify(data.output),
          is_error: 'is_error' in data ? data.is_error : false,
        };
        existingMessage.tool_outputs = [...(existingMessage.tool_outputs || []), toolOutput];
      }
      break;

    default:
      break;
  }
};

export function useAgent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [showThinking, setShowThinking] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const runIdRef = useRef<string | null>(null);

  const addMessage = (message: Message) => {
    setMessages(produce(draft => {
      const existingMessageIndex = draft.findIndex(m => m.id === message.id);
      if (existingMessageIndex !== -1) {
        draft[existingMessageIndex] = message;
      } else {
        draft.push(message);
      }
    }));
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
          const message: StreamEvent = JSON.parse(event.data);
          console.log('Received message:', message);

          if (message.event === 'run_complete') {
            setShowThinking(false);
            return;
          }

          setMessages(produce(draft => processStreamEvent(draft, message)));
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