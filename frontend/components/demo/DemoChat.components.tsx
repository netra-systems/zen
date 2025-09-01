/**
 * DemoChat UI Components
 * Module: Reusable UI components for demo chat interface
 * Lines: <300, Functions: ≤8 lines each
 */

import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Bot, Sparkles, User, Loader2, CheckCircle, AlertCircle, 
  ChevronRight, Clock, Code, TrendingUp, Zap 
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Message, Template, Agent } from './DemoChat.types'

interface ConnectionStatusProps {
  isConnected: boolean
  useWebSocket: boolean
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  isConnected, useWebSocket 
}) => {
  if (!useWebSocket) return null
  
  return (
    <Badge variant={isConnected ? "default" : "secondary"} className="text-xs">
      {isConnected ? (
        <>
          <div className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse" />
          Live
        </>
      ) : (
        <>
          <div className="w-2 h-2 bg-gray-400 rounded-full mr-1" />
          Connecting...
        </>
      )}
    </Badge>
  )
}

interface AgentStatusBarProps {
  agents: Agent[]
  activeAgent: string | null
}

export const AgentStatusBar: React.FC<AgentStatusBarProps> = ({ 
  agents, activeAgent 
}) => (
  <div className="flex items-center gap-2">
    {agents.map(agent => (
      <Badge
        key={agent.id}
        variant={activeAgent === agent.id ? 'default' : 'outline'}
        className={cn(
          "transition-all",
          activeAgent === agent.id && "animate-pulse"
        )}
        data-testid="agent-indicator"
      >
        <span className={agent.color}>{agent.icon}</span>
        <span className="ml-1 text-xs">{agent.name}</span>
      </Badge>
    ))}
  </div>
)

interface MessageBubbleProps {
  message: Message
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => (
  <div className={cn("flex gap-3", message.role === 'user' && "justify-end")}>
    {message.role !== 'user' && (
      <Avatar className="h-8 w-8">
        <AvatarFallback>
          {message.role === 'system' ? <Bot /> : <Sparkles />}
        </AvatarFallback>
      </Avatar>
    )}
    
    <div className={cn("max-w-[80%] space-y-2", message.role === 'user' && "items-end")}>
      <MessageCard message={message} />
      
      {message.role === 'user' && (
        <Avatar className="h-8 w-8 ml-auto">
          <AvatarFallback><User /></AvatarFallback>
        </Avatar>
      )}
    </div>
  </div>
)

const MessageCard: React.FC<{ message: Message }> = ({ message }) => (
  <Card className={cn(message.role === 'user' && "bg-primary text-primary-foreground")}>
    <CardContent className="p-3">
      <div className="text-sm whitespace-pre-wrap">{message.content}</div>
      <MessageMetadata metadata={message.metadata} />
    </CardContent>
  </Card>
)

const MessageMetadata: React.FC<{ metadata?: Message['metadata'] }> = ({ metadata }) => {
  if (!metadata) return null
  
  return (
    <div className="mt-3 pt-3 border-t flex flex-wrap gap-2">
      <MetadataBadge icon={Clock} value={metadata.processingTime} suffix="s" />
      <MetadataBadge icon={Code} value={metadata.tokensUsed} suffix=" tokens" />
      <CostSavingsBadge value={metadata.costSaved} />
      <OptimizationBadge value={metadata.optimizationType} />
    </div>
  )
}

const MetadataBadge: React.FC<{
  icon: React.ComponentType<{ className?: string }>
  value?: number
  suffix: string
}> = ({ icon: Icon, value, suffix }) => {
  if (!value) return null
  
  const displayValue = suffix === "s" ? (value / 1000).toFixed(1) : value
  return (
    <Badge variant="secondary" className="text-xs">
      <Icon className="w-3 h-3 mr-1" />
      {displayValue}{suffix}
    </Badge>
  )
}

const CostSavingsBadge: React.FC<{ value?: number }> = ({ value }) => {
  if (!value) return null
  
  return (
    <Badge variant="default" className="text-xs">
      <TrendingUp className="w-3 h-3 mr-1" />
      ${value.toLocaleString()} saved
    </Badge>
  )
}

const OptimizationBadge: React.FC<{ value?: string }> = ({ value }) => {
  if (!value) return null
  
  return (
    <Badge className="text-xs">
      <Zap className="w-3 h-3 mr-1" />
      {value}
    </Badge>
  )
}

interface ProcessingIndicatorProps {
  agents: Agent[]
  activeAgent: string | null
}

export const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({ 
  agents, activeAgent 
}) => (
  <div className="flex gap-3" data-testid="agent-processing">
    <Avatar className="h-8 w-8">
      <AvatarFallback><Bot /></AvatarFallback>
    </Avatar>
    <Card>
      <CardContent className="p-3">
        <div className="flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm text-muted-foreground">
            Processing
            {activeAgent 
              ? ` - ${agents.find(a => a.id === activeAgent)?.name} is processing...`
              : '...'
            }
          </span>
        </div>
      </CardContent>
    </Card>
  </div>
)

interface TemplateButtonProps {
  template: Template
  onClick: (template: Template) => void
}

export const TemplateButton: React.FC<TemplateButtonProps> = ({ 
  template, onClick 
}) => (
  <Button
    variant="outline"
    className="w-full justify-start text-left h-auto p-3"
    onClick={() => onClick(template)}
  >
    <div className="flex items-start gap-3">
      <div className="mt-0.5">{template.icon}</div>
      <div className="flex-1">
        <div className="font-medium text-sm">{template.title}</div>
        <div className="text-xs text-muted-foreground mt-1">{template.category}</div>
      </div>
      <ChevronRight className="w-4 h-4 mt-0.5 text-muted-foreground" />
    </div>
  </Button>
)

export const OptimizationReadyPanel: React.FC = () => (
  <Card className="border-green-500">
    <CardHeader>
      <CardTitle className="text-lg flex items-center gap-2">
        <CheckCircle className="w-5 h-5 text-green-500" />
        Optimization Ready
      </CardTitle>
    </CardHeader>
    <CardContent>
      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Your optimization plan is ready. View detailed metrics and implementation steps in the Performance tab.
        </AlertDescription>
      </Alert>
      
      <div className="mt-4 space-y-3">
        <MetricRow label="Potential Savings" value="$45K/month" className="text-green-600" />
        <MetricRow label="Performance Gain" value="2.5x faster" />
        <MetricRow label="Implementation Time" value="2-3 weeks" />
      </div>
    </CardContent>
  </Card>
)

const MetricRow: React.FC<{
  label: string
  value: string
  className?: string
}> = ({ label, value, className }) => (
  <div className="flex justify-between text-sm">
    <span className="text-muted-foreground">{label}</span>
    <span className={cn("font-semibold", className)}>{value}</span>
  </div>
)