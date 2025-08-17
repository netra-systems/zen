/**
 * DemoChat Component Types
 * Module: Types and interfaces for demo chat functionality
 * Lines: <300, Functions: ≤8 lines each
 */

export interface DemoChatProps {
  industry: string
  onInteraction?: () => void
  useWebSocket?: boolean
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: MessageMetadata
}

export interface MessageMetadata {
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
  type: 'agent_update' | 'chat_response'
  active_agent?: string
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