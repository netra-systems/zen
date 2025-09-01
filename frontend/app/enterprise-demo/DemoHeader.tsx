'use client';

import { Badge } from '@/components/ui/badge';
import { Sparkles, ChevronRight, CheckCircle, Database, Brain, BarChart3 } from 'lucide-react';
import { demoSteps, getCurrentStepIndex, type DemoStep, type IconType } from './demoConfig';

interface DemoHeaderProps {
  demoStep: DemoStep;
}

const DemoHeader = ({ demoStep }: DemoHeaderProps) => {
  const currentStepIndex = getCurrentStepIndex(demoStep);

  const getIconByType = (iconType: IconType) => {
    switch (iconType) {
      case 'database': return <Database className="w-5 h-5" />;
      case 'sparkles': return <Sparkles className="w-5 h-5" />;
      case 'brain': return <Brain className="w-5 h-5" />;
      case 'barChart3': return <BarChart3 className="w-5 h-5" />;
    }
  };

  const getStepClassName = (index: number) => {
    const isActive = index === currentStepIndex;
    const isCompleted = index < currentStepIndex;
    
    if (isActive) return 'bg-purple-100 text-purple-700';
    if (isCompleted) return 'bg-green-50 text-green-700';
    return 'bg-gray-50 text-gray-400';
  };

  const renderStepIcon = (step: DemoStep, index: number) => {
    const isCompleted = index < currentStepIndex;
    return isCompleted ? <CheckCircle className="w-4 h-4" /> : getIconByType(step.iconType);
  };

  const shouldShowChevron = (index: number) => {
    return index < demoSteps.length - 1;
  };

  return (
    <div className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-30">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Badge variant="secondary" className="glass-accent-purple text-purple-900">
              <Sparkles className="h-3 w-3 mr-1" />
              Enterprise Demo
            </Badge>
            <h1 className="text-xl font-bold text-gray-900">
              Netra AI Optimization Platform
            </h1>
          </div>
          
          {/* Progress Steps */}
          <div className="hidden lg:flex items-center space-x-2">
            {demoSteps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-all ${getStepClassName(index)}`}>
                  {renderStepIcon(step, index)}
                  <span className="text-sm font-medium">{step.title}</span>
                </div>
                {shouldShowChevron(index) && (
                  <ChevronRight className="w-4 h-4 mx-2 text-gray-300" />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DemoHeader;