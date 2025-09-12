/**
 * DemoChat Component Types
 * Module: Types and interfaces for demo chat functionality
 * Lines: <300, Functions: ≤8 lines each
 */

// Import unified Message types from registry
import type { Message, MessageRole } from '@/types/unified';

export interface DemoChatProps {
  industry: string
  onInteraction?: () => void
  useWebSocket?: boolean
}

// Re-export Message from unified registry for convenience
export type { Message };

// Demo-specific metadata extension (backward compatible)
export interface DemoMessageMetadata {
  processingTime?: number
  tokensUsed?: number
  costSaved?: number
  optimizationType?: string
}

export interface Template {
  id: string
  title: string
  prompt: string
  icon: React.ReactNode
  category: string
}

export interface Agent {
  id: string
  name: string
  icon: React.ReactNode
  color: string
}

export interface WebSocketData {
  type: 'agent_started' | 'agent_thinking' | 'tool_executing' | 'tool_completed' | 'agent_completed' | 'agent_update' | 'chat_response'
  active_agent?: string
  agent_name?: string
  response?: string
  optimization_metrics?: OptimizationMetrics
  agents_involved?: string[]
}

export interface OptimizationMetrics {
  estimated_annual_savings?: number
  processing_time?: number
  tokens_used?: number
}

export interface ChatState {
  messages: Message[]
  input: string
  isProcessing: boolean
  activeAgent: string | null
  showOptimization: boolean
}

export type ChatAction = 
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_INPUT'; payload: string }
  | { type: 'SET_PROCESSING'; payload: boolean }
  | { type: 'SET_ACTIVE_AGENT'; payload: string | null }
  | { type: 'SET_SHOW_OPTIMIZATION'; payload: boolean }