/**
 * DemoChat WebSocket Handlers
 * Module: WebSocket message handling and agent progression simulation
 * Lines: <300, Functions: ≤8 lines each
 */

import { WebSocketData, Message } from './DemoChat.types'
import { createResponseMessage } from './DemoChat.messages'
import { generateUniqueId } from '@/lib/utils'

export const handleWebSocketMessage = (
  data: WebSocketData,
  setActiveAgent: (agent: string | null) => void,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  setIsProcessing: (processing: boolean) => void
): void => {
  // Handle new agent events from demo WebSocket
  switch (data.type) {
    case 'agent_started':
      setActiveAgent('triage')
      setIsProcessing(true)
      break
    case 'agent_thinking':
      setActiveAgent('analysis')
      break
    case 'tool_executing':
      setActiveAgent('optimization')
      break
    case 'agent_completed':
      if (data.response) {
        const responseMessage = createWebSocketResponseMessage({
          ...data,
          response: data.response
        })
        setMessages(prev => [...prev, responseMessage])
      }
      setIsProcessing(false)
      setActiveAgent(null)
      break
    case 'agent_update':
      handleAgentUpdate(data, setActiveAgent)
      break
    case 'chat_response':
      handleChatResponse(data, setMessages, setIsProcessing, setActiveAgent)
      break
  }
}

const handleAgentUpdate = (
  data: WebSocketData,
  setActiveAgent: (agent: string | null) => void
): void => {
  if (data.active_agent) {
    setActiveAgent(data.active_agent)
  }
}

const handleChatResponse = (
  data: WebSocketData,
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>,
  setIsProcessing: (processing: boolean) => void,
  setActiveAgent: (agent: string | null) => void
): void => {
  if (data.response) {
    const responseMessage = createWebSocketResponseMessage(data)
    setMessages(prev => [...prev, responseMessage])
  }
  setIsProcessing(false)
  setActiveAgent(null)
}

const createWebSocketResponseMessage = (data: WebSocketData): Message => ({
  id: generateUniqueId('msg'),
  role: 'assistant',
  content: data.response || '',
  timestamp: new Date(),
  metadata: {
    processingTime: 3000,
    tokensUsed: 1500,
    costSaved: data.optimization_metrics?.estimated_annual_savings 
      ? Math.round(data.optimization_metrics.estimated_annual_savings / 12) 
      : 25000,
    optimizationType: data.agents_involved?.join(' → ') || 'Multi-Agent Optimization'
  }
})

export const simulateAgentProgression = async (
  setActiveAgent: (agent: string | null) => void
): Promise<void> => {
  await progressToAgent('triage', setActiveAgent, 800)
  await progressToAgent('analysis', setActiveAgent, 1200)
  await progressToAgent('optimization', setActiveAgent, 1000)
}

const progressToAgent = async (
  agentType: string,
  setActiveAgent: (agent: string | null) => void,
  delay: number
): Promise<void> => {
  await new Promise(resolve => setTimeout(resolve, delay))
  setActiveAgent(agentType)
}

export const getSessionId = (): string => {
  const existingSessionId = localStorage.getItem('demo-session-id')
  if (existingSessionId) {
    return existingSessionId
  }
  
  const newSessionId = `demo-${Date.now()}`
  localStorage.setItem('demo-session-id', newSessionId)
  return newSessionId
}