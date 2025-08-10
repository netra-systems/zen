'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Send, 
  Sparkles, 
  Bot, 
  User, 
  Zap, 
  Brain,
  Activity,
  Code,
  Database,
  Server,
  ChevronRight,
  Loader2,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Clock,
  Shield,
  Heart,
  Search,
  Package
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { demoService } from '@/services/demoService'
import { useDemoWebSocket } from '@/hooks/useDemoWebSocket'

interface DemoChatProps {
  industry: string
  onInteraction?: () => void
  useWebSocket?: boolean
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: {
    processingTime?: number
    tokensUsed?: number
    costSaved?: number
    optimizationType?: string
  }
}

interface Template {
  id: string
  title: string
  prompt: string
  icon: React.ReactNode
  category: string
}

export default function DemoChat({ industry, onInteraction, useWebSocket = false }: DemoChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const [showOptimization, setShowOptimization] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  
  // WebSocket hook for real-time interactions
  const {
    isConnected,
    sendChatMessage: wsSendChatMessage,
  } = useDemoWebSocket({
    onMessage: (data) => {
      if (data.type === 'agent_update') {
        setActiveAgent(data.active_agent)
      } else if (data.type === 'chat_response') {
        const responseMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          metadata: {
            processingTime: 3000,
            tokensUsed: 1500,
            costSaved: data.optimization_metrics?.estimated_annual_savings 
              ? Math.round(data.optimization_metrics.estimated_annual_savings / 12) 
              : 25000,
            optimizationType: data.agents_involved?.join(' → ') || 'Multi-Agent Optimization'
          }
        }
        setMessages(prev => [...prev, responseMessage])
        setIsProcessing(false)
        setActiveAgent(null)
      }
    }
  })

  const industryTemplates: Record<string, Template[]> = {
    'Financial Services': [
      {
        id: 'fraud-1',
        title: 'Optimize Fraud Detection Pipeline',
        prompt: 'Analyze and optimize our fraud detection ML pipeline that processes 10M transactions daily',
        icon: <Shield className="w-4 h-4" />,
        category: 'Security'
      },
      {
        id: 'risk-1',
        title: 'Risk Scoring Performance',
        prompt: 'Improve latency for real-time credit risk scoring models',
        icon: <TrendingUp className="w-4 h-4" />,
        category: 'Analytics'
      },
      {
        id: 'trading-1',
        title: 'Trading Algorithm Optimization',
        prompt: 'Optimize high-frequency trading algorithms for lower latency',
        icon: <Activity className="w-4 h-4" />,
        category: 'Trading'
      }
    ],
    'Healthcare': [
      {
        id: 'diagnostic-1',
        title: 'Medical Image Analysis',
        prompt: 'Optimize diagnostic imaging AI for faster MRI/CT scan analysis',
        icon: <Brain className="w-4 h-4" />,
        category: 'Diagnostics'
      },
      {
        id: 'patient-1',
        title: 'Patient Risk Prediction',
        prompt: 'Improve patient readmission prediction model performance',
        icon: <Heart className="w-4 h-4" />,
        category: 'Patient Care'
      },
      {
        id: 'drug-1',
        title: 'Drug Discovery Pipeline',
        prompt: 'Optimize molecular simulation workloads for drug discovery',
        icon: <Database className="w-4 h-4" />,
        category: 'Research'
      }
    ],
    'E-commerce': [
      {
        id: 'rec-1',
        title: 'Recommendation Engine',
        prompt: 'Optimize product recommendation system serving 100M users',
        icon: <Sparkles className="w-4 h-4" />,
        category: 'Personalization'
      },
      {
        id: 'search-1',
        title: 'Search Optimization',
        prompt: 'Improve search relevance and reduce query latency',
        icon: <Search className="w-4 h-4" />,
        category: 'Search'
      },
      {
        id: 'inventory-1',
        title: 'Inventory Forecasting',
        prompt: 'Optimize demand forecasting models for inventory management',
        icon: <Package className="w-4 h-4" />,
        category: 'Operations'
      }
    ],
    'Technology': [
      {
        id: 'code-1',
        title: 'Code Generation Pipeline',
        prompt: 'Optimize AI code completion service for IDE integration',
        icon: <Code className="w-4 h-4" />,
        category: 'Development'
      },
      {
        id: 'devops-1',
        title: 'CI/CD Optimization',
        prompt: 'Improve AI-powered test generation and deployment validation',
        icon: <Server className="w-4 h-4" />,
        category: 'DevOps'
      },
      {
        id: 'analytics-1',
        title: 'User Analytics AI',
        prompt: 'Optimize real-time user behavior prediction models',
        icon: <Activity className="w-4 h-4" />,
        category: 'Analytics'
      }
    ]
  }

  const defaultTemplates: Template[] = [
    {
      id: 'general-1',
      title: 'Analyze Current Workload',
      prompt: 'Analyze my current AI workload and identify optimization opportunities',
      icon: <Brain className="w-4 h-4" />,
      category: 'Analysis'
    },
    {
      id: 'general-2',
      title: 'Cost Optimization',
      prompt: 'Show me how to reduce AI infrastructure costs without impacting performance',
      icon: <TrendingUp className="w-4 h-4" />,
      category: 'Cost'
    },
    {
      id: 'general-3',
      title: 'Performance Tuning',
      prompt: 'Optimize model inference latency for production workloads',
      icon: <Zap className="w-4 h-4" />,
      category: 'Performance'
    }
  ]

  const templates = industryTemplates[industry] || defaultTemplates

  useEffect(() => {
    // Add welcome message
    const welcomeMessage: Message = {
      id: '1',
      role: 'system',
      content: `Welcome to the Netra AI Optimization Demo! I've loaded industry-specific optimization scenarios for **${industry}**. Select a template below or describe your specific AI workload challenge.`,
      timestamp: new Date()
    }
    setMessages([welcomeMessage])
  }, [industry])

  const simulateAgentResponse = async (userMessage: string) => {
    setIsProcessing(true)
    setActiveAgent('triage')
    
    try {
      // Check if we should use WebSocket for real-time updates
      if (useWebSocket && isConnected) {
        // Send via WebSocket for real-time streaming
        wsSendChatMessage(userMessage, industry)
        // Response will be handled by the WebSocket onMessage handler
        return
      }
      
      // Otherwise use standard HTTP API
      const sessionId = localStorage.getItem('demo-session-id') || `demo-${Date.now()}`
      localStorage.setItem('demo-session-id', sessionId)
      
      // Make API call to backend using demoService
      const data = await demoService.sendChatMessage({
        message: userMessage,
        industry: industry,
        session_id: sessionId,
        context: {}
      })
      
      // Simulate agent progression for visual effect
      await new Promise(resolve => setTimeout(resolve, 800))
      setActiveAgent('analysis')
      await new Promise(resolve => setTimeout(resolve, 1200))
      setActiveAgent('optimization')
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const responseMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        metadata: {
          processingTime: 3000,
          tokensUsed: 1500,
          costSaved: data.optimization_metrics?.estimated_annual_savings 
            ? Math.round(data.optimization_metrics.estimated_annual_savings / 12) 
            : 25000,
          optimizationType: data.agents_involved?.join(' → ') || 'Multi-Agent Optimization'
        }
      }
      
      setMessages(prev => [...prev, responseMessage])
    } catch (error) {
      console.error('Demo chat API error:', error)
      
      // Fallback to simulation if API fails
      await new Promise(resolve => setTimeout(resolve, 800))
      setActiveAgent('analysis')
      await new Promise(resolve => setTimeout(resolve, 1200))
      setActiveAgent('optimization')
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      const optimizationTypes = ['Model Compression', 'Batch Optimization', 'Caching Strategy', 'Infrastructure Scaling', 'Pipeline Parallelization']
      const selectedOptimization = optimizationTypes[Math.floor(Math.random() * optimizationTypes.length)]
      
      const processingTime = 2500 + Math.random() * 1500
      const tokensUsed = 1500 + Math.floor(Math.random() * 1000)
      const costSaved = 15000 + Math.floor(Math.random() * 35000)
      
      const response: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Based on my analysis of your ${industry.toLowerCase()} workload, I've identified significant optimization opportunities:

**Current State Analysis:**
- Processing ${Math.floor(10 + Math.random() * 90)}M requests/month
- Average latency: ${Math.floor(200 + Math.random() * 300)}ms
- Current cost: $${(50000 + Math.random() * 100000).toFixed(0)}/month

**Optimization Strategy: ${selectedOptimization}**
- Reduce latency by ${Math.floor(40 + Math.random() * 30)}%
- Improve throughput by ${Math.floor(2 + Math.random() * 2)}x
- Cost savings: $${costSaved.toLocaleString()}/month

**Implementation Plan:**
1. Deploy intelligent request routing
2. Implement adaptive batching for ${Math.floor(60 + Math.random() * 30)}% of workloads
3. Enable multi-model caching with ${Math.floor(85 + Math.random() * 10)}% hit rate
4. Optimize resource allocation using predictive scaling

**Expected Results:**
- ROI within ${Math.floor(2 + Math.random() * 3)} months
- ${Math.floor(99.9 + Math.random() * 0.09)}% SLA compliance
- ${Math.floor(30 + Math.random() * 30)}% reduction in operational overhead

Would you like me to generate a detailed implementation roadmap or explore specific optimization techniques?`,
        timestamp: new Date(),
        metadata: {
          processingTime: processingTime,
          tokensUsed: tokensUsed,
          costSaved: costSaved,
          optimizationType: selectedOptimization
        }
      }
      
      setMessages(prev => [...prev, response])
    } finally {
      setIsProcessing(false)
      setActiveAgent(null)
      setShowOptimization(true)
      
      if (onInteraction) {
        onInteraction()
      }
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isProcessing) return
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    
    await simulateAgentResponse(input)
  }

  const handleTemplateClick = (template: Template) => {
    setInput(template.prompt)
  }

  const agents = [
    { id: 'triage', name: 'Triage Agent', icon: <Bot className="w-4 h-4" />, color: 'text-blue-500' },
    { id: 'analysis', name: 'Analysis Agent', icon: <Brain className="w-4 h-4" />, color: 'text-purple-500' },
    { id: 'optimization', name: 'Optimization Agent', icon: <Zap className="w-4 h-4" />, color: 'text-green-500' }
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Chat Interface */}
      <div className="lg:col-span-2 space-y-4">
        <Card className="h-[600px] flex flex-col">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  AI Optimization Assistant
                  {useWebSocket && (
                    <Badge 
                      variant={isConnected ? "default" : "secondary"}
                      className="text-xs"
                    >
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
                  )}
                </CardTitle>
                <CardDescription>Powered by multi-agent orchestration</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {agents.map(agent => (
                  <Badge
                    key={agent.id}
                    variant={activeAgent === agent.id ? 'default' : 'outline'}
                    className={cn(
                      "transition-all",
                      activeAgent === agent.id && "animate-pulse"
                    )}
                  >
                    <span className={agent.color}>{agent.icon}</span>
                    <span className="ml-1 text-xs">{agent.name}</span>
                  </Badge>
                ))}
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 flex flex-col p-0">
            <ScrollArea className="flex-1 px-6" ref={scrollAreaRef}>
              <div className="space-y-4 py-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={cn(
                      "flex gap-3",
                      message.role === 'user' && "justify-end"
                    )}
                  >
                    {message.role !== 'user' && (
                      <Avatar className="h-8 w-8">
                        <AvatarFallback>
                          {message.role === 'system' ? <Bot /> : <Sparkles />}
                        </AvatarFallback>
                      </Avatar>
                    )}
                    
                    <div className={cn(
                      "max-w-[80%] space-y-2",
                      message.role === 'user' && "items-end"
                    )}>
                      <Card className={cn(
                        message.role === 'user' && "bg-primary text-primary-foreground"
                      )}>
                        <CardContent className="p-3">
                          <div className="text-sm whitespace-pre-wrap">{message.content}</div>
                          
                          {message.metadata && (
                            <div className="mt-3 pt-3 border-t flex flex-wrap gap-2">
                              {message.metadata.processingTime && (
                                <Badge variant="secondary" className="text-xs">
                                  <Clock className="w-3 h-3 mr-1" />
                                  {(message.metadata.processingTime / 1000).toFixed(1)}s
                                </Badge>
                              )}
                              {message.metadata.tokensUsed && (
                                <Badge variant="secondary" className="text-xs">
                                  <Code className="w-3 h-3 mr-1" />
                                  {message.metadata.tokensUsed} tokens
                                </Badge>
                              )}
                              {message.metadata.costSaved && (
                                <Badge variant="default" className="text-xs">
                                  <TrendingUp className="w-3 h-3 mr-1" />
                                  ${message.metadata.costSaved.toLocaleString()} saved
                                </Badge>
                              )}
                              {message.metadata.optimizationType && (
                                <Badge className="text-xs">
                                  <Zap className="w-3 h-3 mr-1" />
                                  {message.metadata.optimizationType}
                                </Badge>
                              )}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                      
                      {message.role === 'user' && (
                        <Avatar className="h-8 w-8 ml-auto">
                          <AvatarFallback><User /></AvatarFallback>
                        </Avatar>
                      )}
                    </div>
                  </div>
                ))}
                
                {isProcessing && (
                  <div className="flex gap-3">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback><Bot /></AvatarFallback>
                    </Avatar>
                    <Card>
                      <CardContent className="p-3">
                        <div className="flex items-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-sm text-muted-foreground">
                            {activeAgent ? `${agents.find(a => a.id === activeAgent)?.name} is processing...` : 'Processing...'}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}
              </div>
            </ScrollArea>
            
            <div className="p-6 border-t">
              <div className="flex gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder="Describe your AI workload optimization needs..."
                  className="min-h-[60px] resize-none"
                  disabled={isProcessing}
                />
                <Button 
                  onClick={handleSend}
                  disabled={!input.trim() || isProcessing}
                  className="px-4"
                >
                  {isProcessing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Templates and Insights Panel */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Templates</CardTitle>
            <CardDescription>Industry-specific optimization scenarios</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[250px]">
              <div className="space-y-2">
                {templates.map((template) => (
                  <Button
                    key={template.id}
                    variant="outline"
                    className="w-full justify-start text-left h-auto p-3"
                    onClick={() => handleTemplateClick(template)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">{template.icon}</div>
                      <div className="flex-1">
                        <div className="font-medium text-sm">{template.title}</div>
                        <div className="text-xs text-muted-foreground mt-1">
                          {template.category}
                        </div>
                      </div>
                      <ChevronRight className="w-4 h-4 mt-0.5 text-muted-foreground" />
                    </div>
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {showOptimization && (
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
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Potential Savings</span>
                  <span className="font-semibold text-green-600">$45K/month</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Performance Gain</span>
                  <span className="font-semibold">2.5x faster</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Implementation Time</span>
                  <span className="font-semibold">2-3 weeks</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}