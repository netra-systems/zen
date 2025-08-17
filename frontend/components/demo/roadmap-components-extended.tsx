// Implementation Roadmap Extended Components
// Module: Additional UI components for roadmap functionality  
// Max 300 lines, all functions ≤8 lines

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { 
  CheckCircle2,
  ArrowRight,
  AlertTriangle,
  Mail
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Phase, Task, SupportOption, RiskMitigation } from './roadmap-types'

// Task breakdown card (≤8 lines)
export const TaskBreakdownCard = ({ phases }: { phases: Phase[] }) => (
  <Card>
    <CardHeader>
      <CardTitle>Complete Task List</CardTitle>
      <CardDescription>All tasks required for successful implementation</CardDescription>
    </CardHeader>
    <CardContent>
      <TaskBreakdownContent phases={phases} />
    </CardContent>
  </Card>
)

// Task breakdown content (≤8 lines)
const TaskBreakdownContent = ({ phases }: { phases: Phase[] }) => (
  <div className="space-y-6">
    {phases.map(phase => (
      <PhaseTaskSection key={phase.id} phase={phase} />
    ))}
  </div>
)

// Phase task section (≤8 lines)
const PhaseTaskSection = ({ phase }: { phase: Phase }) => (
  <div>
    <h3 className="font-semibold mb-3">{phase.name}</h3>
    <div className="space-y-2">
      {phase.tasks.map(task => (
        <TaskCard key={task.id} task={task} />
      ))}
    </div>
  </div>
)

// Individual task card (≤8 lines)
const TaskCard = ({ task }: { task: Task }) => (
  <Card>
    <CardContent className="p-3">
      <div className="flex items-center justify-between">
        <TaskInfo task={task} />
        <TaskDetails task={task} />
      </div>
    </CardContent>
  </Card>
)

// Task info (≤8 lines)
const TaskInfo = ({ task }: { task: Task }) => (
  <div className="flex items-center gap-3">
    <TaskPriorityBadge priority={task.priority} />
    <span className="text-sm">{task.title}</span>
  </div>
)

// Task priority badge (≤8 lines)
const TaskPriorityBadge = ({ priority }: { priority: string }) => (
  <Badge variant={
    priority === 'critical' ? 'destructive' :
    priority === 'high' ? 'default' :
    'outline'
  }>
    {priority}
  </Badge>
)

// Task details (≤8 lines)
const TaskDetails = ({ task }: { task: Task }) => (
  <div className="flex items-center gap-4 text-xs text-muted-foreground">
    <span>{task.owner}</span>
    <span>{task.effort}</span>
  </div>
)

// Risk management card (≤8 lines)
export const RiskManagementCard = ({ 
  riskMitigations 
}: { 
  riskMitigations: RiskMitigation[] 
}) => (
  <Card>
    <CardHeader>
      <CardTitle>Risk Mitigation Strategy</CardTitle>
      <CardDescription>Proactive measures to ensure successful deployment</CardDescription>
    </CardHeader>
    <CardContent>
      <RiskMitigationList riskMitigations={riskMitigations} />
    </CardContent>
  </Card>
)

// Risk mitigation list (≤8 lines)
const RiskMitigationList = ({ 
  riskMitigations 
}: { 
  riskMitigations: RiskMitigation[] 
}) => (
  <div className="space-y-4">
    {riskMitigations.map((item, idx) => (
      <RiskMitigationCard key={idx} risk={item} />
    ))}
  </div>
)

// Risk mitigation card (≤8 lines)
const RiskMitigationCard = ({ risk }: { risk: RiskMitigation }) => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-start gap-3">
        <RiskIcon severity={risk.severity} />
        <RiskContent risk={risk} />
        <SeverityBadge severity={risk.severity} />
      </div>
    </CardContent>
  </Card>
)

// Risk icon (≤8 lines)
const RiskIcon = ({ severity }: { severity: string }) => (
  <AlertTriangle className={cn(
    "w-5 h-5 mt-0.5",
    severity === 'low' && "text-yellow-500",
    severity === 'medium' && "text-orange-500",
    severity === 'high' && "text-red-500"
  )} />
)

// Risk content (≤8 lines)
const RiskContent = ({ risk }: { risk: RiskMitigation }) => (
  <div className="flex-1">
    <h4 className="font-medium text-sm mb-1">{risk.risk}</h4>
    <p className="text-sm text-muted-foreground">{risk.mitigation}</p>
  </div>
)

// Severity badge (≤8 lines)
const SeverityBadge = ({ severity }: { severity: string }) => (
  <Badge variant={
    severity === 'low' ? 'outline' :
    severity === 'medium' ? 'secondary' :
    'destructive'
  }>
    {severity}
  </Badge>
)

// Support package card (≤8 lines)
export const SupportPackageCard = ({ 
  supportOptions 
}: { 
  supportOptions: SupportOption[] 
}) => (
  <Card>
    <CardHeader>
      <CardTitle>Enterprise Support Package</CardTitle>
      <CardDescription>Comprehensive support for your implementation journey</CardDescription>
    </CardHeader>
    <CardContent>
      <SupportContent supportOptions={supportOptions} />
    </CardContent>
  </Card>
)

// Support content (≤8 lines)
const SupportContent = ({ 
  supportOptions 
}: { 
  supportOptions: SupportOption[] 
}) => (
  <>
    <SupportOptionsGrid supportOptions={supportOptions} />
    <SupportContactAlert />
  </>
)

// Support options grid (≤8 lines)
const SupportOptionsGrid = ({ 
  supportOptions 
}: { 
  supportOptions: SupportOption[] 
}) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    {supportOptions.map((option, idx) => (
      <SupportOptionCard key={idx} option={option} />
    ))}
  </div>
)

// Support option card (≤8 lines)
const SupportOptionCard = ({ option }: { option: SupportOption }) => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-start gap-3">
        <SupportIcon icon={option.icon} />
        <SupportDetails option={option} />
        {option.available && <CheckCircle2 className="w-5 h-5 text-green-600" />}
      </div>
    </CardContent>
  </Card>
)

// Support icon (≤8 lines)
const SupportIcon = ({ icon }: { icon: React.ReactNode }) => (
  <div className="p-2 bg-primary/10 rounded-lg">
    {icon}
  </div>
)

// Support details (≤8 lines)
const SupportDetails = ({ option }: { option: SupportOption }) => (
  <div className="flex-1">
    <h4 className="font-medium text-sm mb-1">{option.title}</h4>
    <p className="text-xs text-muted-foreground">{option.description}</p>
  </div>
)

// Support contact alert (≤8 lines)
const SupportContactAlert = () => (
  <Alert className="mt-6">
    <Mail className="h-4 w-4" />
    <AlertTitle>Ready to Start?</AlertTitle>
    <AlertDescription>
      Contact your dedicated success manager at success@netrasystems.ai or call 1-800-NETRA-AI
    </AlertDescription>
  </Alert>
)

// Call to action card (≤8 lines)
export const CallToActionCard = () => (
  <Card className="border-2 border-primary">
    <CardContent className="p-6">
      <div className="flex items-center justify-between">
        <CTAContent />
        <CTAButtons />
      </div>
    </CardContent>
  </Card>
)

// CTA content (≤8 lines)
const CTAContent = () => (
  <div>
    <h3 className="text-lg font-semibold mb-2">Ready to Transform Your AI Infrastructure?</h3>
    <p className="text-sm text-muted-foreground">
      Join 2,500+ companies optimizing their AI workloads with Netra
    </p>
  </div>
)

// CTA buttons (≤8 lines)
const CTAButtons = () => (
  <div className="flex gap-3">
    <Button variant="outline">
      Schedule Call
    </Button>
    <Button className="bg-gradient-to-r from-emerald-600 to-purple-600">
      Start Pilot Program
      <ArrowRight className="w-4 h-4 ml-2" />
    </Button>
  </div>
)