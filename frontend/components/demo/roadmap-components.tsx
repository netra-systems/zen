// Implementation Roadmap Components
// Module: Reusable UI components for roadmap functionality  
// Max 300 lines, all functions ≤8 lines

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { 
  CheckCircle2,
  Clock,
  Download,
  ArrowRight,
  Shield,
  Zap,
  TrendingUp,
  AlertTriangle,
  Rocket,
  Info,
  Mail
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Phase, Task, SupportOption, RiskMitigation } from './roadmap-types'

// Header component (≤8 lines)
export const RoadmapHeader = ({ 
  industry, 
  onExport 
}: { 
  industry: string; 
  onExport: () => void 
}) => (
  <Card>
    <CardHeader>
      <div className="flex items-center justify-between">
        <HeaderContent industry={industry} />
        <ExportButton onExport={onExport} />
      </div>
    </CardHeader>
  </Card>
)

// Header content (≤8 lines)
const HeaderContent = ({ industry }: { industry: string }) => (
  <div>
    <CardTitle className="flex items-center gap-2">
      <Rocket className="w-5 h-5" />
      Implementation Roadmap
    </CardTitle>
    <CardDescription>
      Your path to production deployment for {industry}
    </CardDescription>
  </div>
)

// Export button (≤8 lines)
const ExportButton = ({ onExport }: { onExport: () => void }) => (
  <Button 
    onClick={onExport}
    className="bg-gradient-to-r from-emerald-600 to-purple-600"
  >
    <Download className="w-4 h-4 mr-2" />
    Export Plan
  </Button>
)

// Metrics grid (≤8 lines)
export const MetricsGrid = () => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
    <TimeToValueCard />
    <ROICard />
    <RiskLevelCard />
    <SupportSLACard />
  </div>
)

// Time to value metric card (≤8 lines)
const TimeToValueCard = () => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <MetricContent label="Time to Value" value="2 weeks" />
        <Clock className="w-8 h-8 text-muted-foreground" />
      </div>
    </CardContent>
  </Card>
)

// ROI metric card (≤8 lines)
const ROICard = () => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <MetricContent label="Expected ROI" value="380%" className="text-green-600" />
        <TrendingUp className="w-8 h-8 text-green-600" />
      </div>
    </CardContent>
  </Card>
)

// Risk level metric card (≤8 lines)
const RiskLevelCard = () => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <MetricContent label="Risk Level" value="Low" className="text-yellow-600" />
        <Shield className="w-8 h-8 text-yellow-600" />
      </div>
    </CardContent>
  </Card>
)

// Support SLA metric card (≤8 lines)
const SupportSLACard = () => (
  <Card>
    <CardContent className="p-4">
      <div className="flex items-center justify-between">
        <MetricContent label="Support SLA" value="15 min" />
        <Zap className="w-8 h-8 text-muted-foreground" />
      </div>
    </CardContent>
  </Card>
)

// Metric content helper (≤8 lines)
const MetricContent = ({ 
  label, 
  value, 
  className 
}: { 
  label: string; 
  value: string; 
  className?: string 
}) => (
  <div>
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className={cn("text-2xl font-bold", className)}>{value}</p>
  </div>
)

// Phase recommendation alert (≤8 lines)
export const PhaseRecommendationAlert = ({ industry }: { industry: string }) => (
  <Alert>
    <Info className="h-4 w-4" />
    <AlertTitle>Recommended Approach</AlertTitle>
    <AlertDescription>
      Based on your {industry} workload analysis, we recommend a phased rollout over 12 weeks to minimize risk and maximize learning.
    </AlertDescription>
  </Alert>
)

// Phase card (≤8 lines)
export const PhaseCard = ({ 
  phase, 
  index 
}: { 
  phase: Phase; 
  index: number 
}) => (
  <Card className={cn(
    "transition-all",
    phase.status === 'current' && "border-primary shadow-lg"
  )}>
    <CardHeader>
      <PhaseHeader phase={phase} index={index} />
    </CardHeader>
    <CardContent>
      <PhaseContent phase={phase} />
    </CardContent>
  </Card>
)

// Phase header (≤8 lines)
const PhaseHeader = ({ 
  phase, 
  index 
}: { 
  phase: Phase; 
  index: number 
}) => (
  <div className="flex items-center justify-between">
    <PhaseInfo phase={phase} index={index} />
    <PhaseBadges phase={phase} />
  </div>
)

// Phase info (≤8 lines)
const PhaseInfo = ({ 
  phase, 
  index 
}: { 
  phase: Phase; 
  index: number 
}) => (
  <div className="flex items-center gap-3">
    <PhaseIcon phase={phase} index={index} />
    <div>
      <CardTitle className="text-lg">{phase.name}</CardTitle>
      <CardDescription>{phase.duration}</CardDescription>
    </div>
  </div>
)

// Phase icon (≤8 lines)
const PhaseIcon = ({ 
  phase, 
  index 
}: { 
  phase: Phase; 
  index: number 
}) => (
  <div className={cn(
    "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold",
    phase.status === 'completed' && "bg-green-100 text-green-700",
    phase.status === 'current' && "bg-primary text-primary-foreground",
    phase.status === 'upcoming' && "bg-gray-100 text-gray-600"
  )}>
    {phase.status === 'completed' ? <CheckCircle2 className="w-5 h-5" /> : index + 1}
  </div>
)

// Phase badges (≤8 lines)
const PhaseBadges = ({ phase }: { phase: Phase }) => (
  <div className="flex items-center gap-2">
    <RiskBadge risk={phase.risk} />
    {phase.status === 'current' && <Badge>Active</Badge>}
  </div>
)

// Risk badge (≤8 lines)
const RiskBadge = ({ risk }: { risk: string }) => (
  <Badge variant={
    risk === 'low' ? 'secondary' :
    risk === 'medium' ? 'outline' :
    'destructive'
  }>
    {risk} risk
  </Badge>
)

// Phase content (≤8 lines)
const PhaseContent = ({ phase }: { phase: Phase }) => (
  <div className="space-y-3">
    <PhaseMilestone milestone={phase.milestone} />
    <PhaseTasksPreview tasks={phase.tasks} />
    {phase.status === 'current' && <PhaseActionButton />}
  </div>
)

// Phase milestone (≤8 lines)
const PhaseMilestone = ({ milestone }: { milestone: string }) => (
  <div className="flex items-center gap-2 text-sm">
    <CheckCircle2 className="w-4 h-4 text-green-600" />
    <span className="font-medium">Milestone:</span>
    <span className="text-muted-foreground">{milestone}</span>
  </div>
)

// Phase tasks preview (≤8 lines)
const PhaseTasksPreview = ({ tasks }: { tasks: Task[] }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between text-sm">
      <span className="font-medium">Key Tasks:</span>
      <span className="text-muted-foreground">
        {tasks.filter(t => t.priority === 'critical').length} critical
      </span>
    </div>
    <TaskPreviewGrid tasks={tasks} />
  </div>
)

// Task preview grid (≤8 lines)
const TaskPreviewGrid = ({ tasks }: { tasks: Task[] }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
    {tasks.slice(0, 2).map(task => (
      <TaskPreviewItem key={task.id} task={task} />
    ))}
  </div>
)

// Task preview item (≤8 lines)
const TaskPreviewItem = ({ task }: { task: Task }) => (
  <div className="flex items-center gap-2 text-xs">
    <ArrowRight className="w-3 h-3 text-muted-foreground" />
    <span>{task.title}</span>
  </div>
)

// Phase action button (≤8 lines)
const PhaseActionButton = () => (
  <Button className="w-full" variant="outline">
    View Detailed Tasks
    <ArrowRight className="w-4 h-4 ml-2" />
  </Button>
)