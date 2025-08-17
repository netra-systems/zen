'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { Agent } from './types'

interface AgentCardProps {
  agent: Agent
}

export default function AgentCard({ agent }: AgentCardProps) {
  const getStatusVariant = () => {
    return agent.status === 'processing' ? 'default' :
           agent.status === 'completed' ? 'secondary' : 'outline'
  }

  const getIconContainerClass = () => {
    return cn("p-2 rounded-lg", 
      agent.status === 'processing' && "bg-primary/10 animate-pulse",
      agent.status === 'completed' && "bg-green-100 dark:bg-green-900",
      agent.status === 'idle' && "bg-gray-100 dark:bg-gray-800"
    )
  }

  return (
    <Card className={cn(
      "transition-all",
      agent.status === 'processing' && "border-primary shadow-md"
    )}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className={getIconContainerClass()}>
              <span className={agent.color}>{agent.icon}</span>
            </div>
            <div>
              <h4 className="font-medium text-sm">{agent.name}</h4>
              <p className="text-xs text-muted-foreground">{agent.role}</p>
            </div>
          </div>
          <Badge variant={getStatusVariant()}>
            {agent.status}
          </Badge>
        </div>
        
        {agent.tasks > 0 && (
          <div className="space-y-2 mt-3 pt-3 border-t">
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Tasks:</span>
              <span>{agent.completedTasks}/{agent.tasks}</span>
            </div>
            {agent.processingTime && (
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Processing:</span>
                <span>{agent.processingTime}ms</span>
              </div>
            )}
            {agent.confidence && (
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Confidence:</span>
                <span className="font-medium">{agent.confidence}%</span>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}