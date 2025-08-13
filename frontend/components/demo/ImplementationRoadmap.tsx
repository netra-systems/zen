'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  CheckCircle2,
  Clock,
  Download,
  FileText,
  ArrowRight,
  Users,
  Shield,
  Zap,
  TrendingUp,
  AlertTriangle,
  Info,
  Mail,
  Phone,
  MessageSquare,
  Rocket
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImplementationRoadmapProps {
  industry: string
  completedSteps: string[]
  onExport?: () => void
}

interface Phase {
  id: string
  name: string
  duration: string
  status: 'current' | 'upcoming' | 'completed'
  tasks: Task[]
  milestone: string
  risk: 'low' | 'medium' | 'high'
}

interface Task {
  id: string
  title: string
  owner: string
  priority: 'critical' | 'high' | 'medium' | 'low'
  effort: string
}

export default function ImplementationRoadmap({ 
  industry, 
  completedSteps,
  onExport 
}: ImplementationRoadmapProps) {
  const [activeTab, setActiveTab] = useState('phases')
  const [exportFormat] = useState<'pdf' | 'json' | 'csv'>('pdf')

  const phases: Phase[] = [
    {
      id: 'immediate',
      name: 'Immediate Actions',
      duration: 'Week 1',
      status: 'current',
      tasks: [
        {
          id: 't1',
          title: 'Share optimization report with stakeholders',
          owner: 'Project Lead',
          priority: 'critical',
          effort: '2 hours'
        },
        {
          id: 't2',
          title: 'Schedule technical deep-dive with engineering',
          owner: 'Tech Lead',
          priority: 'high',
          effort: '1 hour'
        },
        {
          id: 't3',
          title: 'Identify pilot workloads for testing',
          owner: 'Engineering',
          priority: 'high',
          effort: '4 hours'
        }
      ],
      milestone: 'Stakeholder alignment achieved',
      risk: 'low'
    },
    {
      id: 'pilot',
      name: 'Pilot Implementation',
      duration: 'Weeks 2-3',
      status: 'upcoming',
      tasks: [
        {
          id: 't4',
          title: 'Deploy Netra agents in dev environment',
          owner: 'DevOps',
          priority: 'critical',
          effort: '2 days'
        },
        {
          id: 't5',
          title: 'Configure monitoring and observability',
          owner: 'SRE Team',
          priority: 'high',
          effort: '1 day'
        },
        {
          id: 't6',
          title: 'Run A/B tests with 10% traffic',
          owner: 'Engineering',
          priority: 'high',
          effort: '3 days'
        },
        {
          id: 't7',
          title: 'Collect performance metrics',
          owner: 'Data Team',
          priority: 'medium',
          effort: '2 days'
        }
      ],
      milestone: 'Pilot validation complete',
      risk: 'medium'
    },
    {
      id: 'scaling',
      name: 'Gradual Scaling',
      duration: 'Weeks 4-6',
      status: 'upcoming',
      tasks: [
        {
          id: 't8',
          title: 'Scale to 25% of production traffic',
          owner: 'Engineering',
          priority: 'critical',
          effort: '3 days'
        },
        {
          id: 't9',
          title: 'Implement auto-scaling policies',
          owner: 'DevOps',
          priority: 'high',
          effort: '2 days'
        },
        {
          id: 't10',
          title: 'Train team on Netra platform',
          owner: 'Training Team',
          priority: 'medium',
          effort: '1 week'
        }
      ],
      milestone: 'Quarter production deployment',
      risk: 'medium'
    },
    {
      id: 'production',
      name: 'Full Production',
      duration: 'Weeks 7-12',
      status: 'upcoming',
      tasks: [
        {
          id: 't11',
          title: 'Complete production rollout',
          owner: 'Engineering',
          priority: 'critical',
          effort: '1 week'
        },
        {
          id: 't12',
          title: 'Optimize based on real-world data',
          owner: 'ML Team',
          priority: 'high',
          effort: '2 weeks'
        },
        {
          id: 't13',
          title: 'Document best practices',
          owner: 'Tech Writers',
          priority: 'low',
          effort: '3 days'
        }
      ],
      milestone: 'Full production deployment',
      risk: 'high'
    }
  ]

  const supportOptions = [
    {
      title: '24/7 Enterprise Support',
      description: 'Round-the-clock support with 15-minute SLA',
      icon: <Phone className="w-5 h-5" />,
      available: true
    },
    {
      title: 'Dedicated Success Manager',
      description: 'Personal point of contact for your implementation',
      icon: <Users className="w-5 h-5" />,
      available: true
    },
    {
      title: 'Slack Connect Channel',
      description: 'Direct access to our engineering team',
      icon: <MessageSquare className="w-5 h-5" />,
      available: true
    },
    {
      title: 'Training & Certification',
      description: 'Comprehensive training for your team',
      icon: <FileText className="w-5 h-5" />,
      available: true
    }
  ]

  const riskMitigations = [
    {
      risk: 'Performance degradation during rollout',
      mitigation: 'Instant rollback capability with zero downtime',
      severity: 'medium'
    },
    {
      risk: 'Integration challenges with existing stack',
      mitigation: 'Pre-built connectors and professional services support',
      severity: 'low'
    },
    {
      risk: 'Team adoption and learning curve',
      mitigation: 'Comprehensive training program and documentation',
      severity: 'low'
    },
    {
      risk: 'Cost overruns during implementation',
      mitigation: 'Fixed-price implementation package available',
      severity: 'medium'
    }
  ]

  const handleExport = () => {
    const exportData = {
      industry,
      completedSteps,
      phases,
      supportOptions,
      riskMitigations,
      exportDate: new Date().toISOString(),
      estimatedSavings: '$540,000/year',
      implementationCost: '$50,000 one-time'
    }

    if (exportFormat === 'json') {
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `netra-implementation-roadmap-${Date.now()}.json`
      a.click()
    } else {
      // For PDF and CSV, we'd normally use a library like jsPDF or Papa Parse
      alert(`Export to ${exportFormat.toUpperCase()} would be implemented with appropriate libraries`)
    }

    if (onExport) {
      onExport()
    }
  }

  // Removed unused function - phase progress handled by getPhaseCompletion

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Rocket className="w-5 h-5" />
                Implementation Roadmap
              </CardTitle>
              <CardDescription>
                Your path to production deployment for {industry}
              </CardDescription>
            </div>
            <Button 
              onClick={handleExport}
              className="bg-gradient-to-r from-emerald-600 to-purple-600"
            >
              <Download className="w-4 h-4 mr-2" />
              Export Plan
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Key Metrics Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Time to Value</p>
                <p className="text-2xl font-bold">2 weeks</p>
              </div>
              <Clock className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Expected ROI</p>
                <p className="text-2xl font-bold text-green-600">380%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Risk Level</p>
                <p className="text-2xl font-bold text-yellow-600">Low</p>
              </div>
              <Shield className="w-8 h-8 text-yellow-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Support SLA</p>
                <p className="text-2xl font-bold">15 min</p>
              </div>
              <Zap className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="phases">Implementation Phases</TabsTrigger>
          <TabsTrigger value="tasks">Task Breakdown</TabsTrigger>
          <TabsTrigger value="risks">Risk Management</TabsTrigger>
          <TabsTrigger value="support">Support & Resources</TabsTrigger>
        </TabsList>

        <TabsContent value="phases" className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Recommended Approach</AlertTitle>
            <AlertDescription>
              Based on your {industry} workload analysis, we recommend a phased rollout over 12 weeks to minimize risk and maximize learning.
            </AlertDescription>
          </Alert>

          <div className="space-y-4">
            {phases.map((phase, idx) => (
              <Card key={phase.id} className={cn(
                "transition-all",
                phase.status === 'current' && "border-primary shadow-lg"
              )}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
                        phase.status === 'completed' && "bg-green-100 text-green-700",
                        phase.status === 'current' && "bg-primary text-primary-foreground",
                        phase.status === 'upcoming' && "bg-gray-100 text-gray-600"
                      )}>
                        {phase.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : idx + 1}
                      </div>
                      <div>
                        <CardTitle className="text-lg">{phase.name}</CardTitle>
                        <CardDescription>{phase.duration}</CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={
                        phase.risk === 'low' ? 'secondary' :
                        phase.risk === 'medium' ? 'outline' :
                        'destructive'
                      }>
                        {phase.risk} risk
                      </Badge>
                      {phase.status === 'current' && (
                        <Badge>Active</Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-sm">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                      <span className="font-medium">Milestone:</span>
                      <span className="text-muted-foreground">{phase.milestone}</span>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">Key Tasks:</span>
                        <span className="text-muted-foreground">
                          {phase.tasks.filter(t => t.priority === 'critical').length} critical
                        </span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {phase.tasks.slice(0, 2).map(task => (
                          <div key={task.id} className="flex items-center gap-2 text-xs">
                            <ArrowRight className="w-3 h-3 text-muted-foreground" />
                            <span>{task.title}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    {phase.status === 'current' && (
                      <Button className="w-full" variant="outline">
                        View Detailed Tasks
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="tasks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Complete Task List</CardTitle>
              <CardDescription>All tasks required for successful implementation</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {phases.map(phase => (
                  <div key={phase.id}>
                    <h3 className="font-semibold mb-3">{phase.name}</h3>
                    <div className="space-y-2">
                      {phase.tasks.map(task => (
                        <Card key={task.id}>
                          <CardContent className="p-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <Badge variant={
                                  task.priority === 'critical' ? 'destructive' :
                                  task.priority === 'high' ? 'default' :
                                  'outline'
                                }>
                                  {task.priority}
                                </Badge>
                                <span className="text-sm">{task.title}</span>
                              </div>
                              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                <span>{task.owner}</span>
                                <span>{task.effort}</span>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="risks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Risk Mitigation Strategy</CardTitle>
              <CardDescription>Proactive measures to ensure successful deployment</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {riskMitigations.map((item, idx) => (
                  <Card key={idx}>
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <AlertTriangle className={cn(
                          "w-5 h-5 mt-0.5",
                          item.severity === 'low' && "text-yellow-500",
                          item.severity === 'medium' && "text-orange-500",
                          item.severity === 'high' && "text-red-500"
                        )} />
                        <div className="flex-1">
                          <h4 className="font-medium text-sm mb-1">{item.risk}</h4>
                          <p className="text-sm text-muted-foreground">{item.mitigation}</p>
                        </div>
                        <Badge variant={
                          item.severity === 'low' ? 'outline' :
                          item.severity === 'medium' ? 'secondary' :
                          'destructive'
                        }>
                          {item.severity}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="support" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Enterprise Support Package</CardTitle>
              <CardDescription>Comprehensive support for your implementation journey</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {supportOptions.map((option, idx) => (
                  <Card key={idx}>
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-primary/10 rounded-lg">
                          {option.icon}
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium text-sm mb-1">{option.title}</h4>
                          <p className="text-xs text-muted-foreground">{option.description}</p>
                        </div>
                        {option.available && (
                          <CheckCircle2 className="w-5 h-5 text-green-600" />
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              
              <Alert className="mt-6">
                <Mail className="h-4 w-4" />
                <AlertTitle>Ready to Start?</AlertTitle>
                <AlertDescription>
                  Contact your dedicated success manager at success@netra.ai or call 1-800-NETRA-AI
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Call to Action */}
      <Card className="border-2 border-primary">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold mb-2">Ready to Transform Your AI Infrastructure?</h3>
              <p className="text-sm text-muted-foreground">
                Join 2,500+ companies optimizing their AI workloads with Netra
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline">
                Schedule Call
              </Button>
              <Button className="bg-gradient-to-r from-emerald-600 to-purple-600">
                Start Pilot Program
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}