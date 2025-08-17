export type DemoStep = 'welcome' | 'workload' | 'generating' | 'analyzing' | 'results';

export type IconType = 'database' | 'sparkles' | 'brain' | 'barChart3';

export interface DemoStepConfig {
  id: string;
  title: string;
  description: string;
  iconType: IconType;
}

export const demoSteps: DemoStepConfig[] = [
  {
    id: 'workload',
    title: 'Select Workload',
    description: 'Choose your industry profile',
    iconType: 'database'
  },
  {
    id: 'generate',
    title: 'Generate Data',
    description: 'Create synthetic workload data',
    iconType: 'sparkles'
  },
  {
    id: 'analyze',
    title: 'Analyze & Optimize',
    description: 'AI-powered optimization',
    iconType: 'brain'
  },
  {
    id: 'results',
    title: 'View Results',
    description: 'See optimization metrics',
    iconType: 'barChart3'
  }
];

export const getCurrentStepIndex = (demoStep: DemoStep): number => {
  switch(demoStep) {
    case 'welcome': return -1;
    case 'workload': return 0;
    case 'generating': return 1;
    case 'analyzing': return 2;
    case 'results': return 3;
    default: return 0;
  }
};

export const getMetrics = () => ({
  savings: '$2.4M',
  performance: '3.2x',
  uptime: '99.9%'
});

export const getResultsData = () => ({
  costReduction: 42,
  monthlySavings: '$124K',
  responseTime: '3.2x',
  latencyImprovement: '62ms → 19ms p50',
  reliability: '99.9%',
  reliabilityFrom: 'From 97.2%',
  gpuUtilization: '85%',
  gpuFrom: 'From 45%'
});