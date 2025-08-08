"use client";
import { createContext, useContext, useReducer, ReactNode } from 'react';
import { Message, SubAgentStatus } from '@/types';

interface ChatState {
  messages: Message[];
  subAgentStatus: SubAgentStatus | null;
  error: string | null;
}

type ChatAction = 
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_SUB_AGENT_STATUS'; payload: SubAgentStatus }
  | { type: 'SET_ERROR'; payload: string | null };

const initialState: ChatState = {
  messages: [],
  subAgentStatus: null,
  error: null,
};

const ChatContext = createContext<{ state: ChatState; dispatch: React.Dispatch<ChatAction> } | undefined>(undefined);

const chatReducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_SUB_AGENT_STATUS':
      return { ...state, subAgentStatus: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
};

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer(chatReducer, initialState);

  return (
    <ChatContext.Provider value={{ state, dispatch }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};