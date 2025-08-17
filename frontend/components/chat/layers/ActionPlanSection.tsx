// Action Plan Section Component
// Business Value: Implementation guidance for Enterprise customer self-service

import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ActionStep {
  id: string;
  step_number: number;
  description: string;
  command?: string;
  expected_outcome: string;
}

interface ActionPlanSectionProps {
  actionPlan: ActionStep[];
}

export const ActionPlanSection: React.FC<ActionPlanSectionProps> = ({ 
  actionPlan 
}) => {
  if (!actionPlan || actionPlan.length === 0) {
    return null;
  }

  return (
    <div>
      <ActionPlanHeader />
      <ActionPlanList actionPlan={actionPlan} />
    </div>
  );
};

const ActionPlanHeader = () => (
  <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
    <AlertCircle className="w-4 h-4 mr-2 text-orange-600" />
    Implementation Action Plan
  </h3>
);

const ActionPlanList = ({ actionPlan }: { actionPlan: ActionStep[] }) => (
  <div className="bg-white rounded-lg p-4 border border-gray-200">
    <ol className="space-y-3">
      {actionPlan.map((step) => (
        <ActionPlanItem key={step.id} step={step} />
      ))}
    </ol>
  </div>
);

const ActionPlanItem = ({ step }: { step: ActionStep }) => (
  <li className="flex">
    <ActionStepNumber stepNumber={step.step_number} />
    <ActionStepContent step={step} />
  </li>
);

const ActionStepNumber = ({ stepNumber }: { stepNumber: number }) => (
  <span className="font-mono text-xs text-gray-500 mr-3 mt-0.5">
    {String(stepNumber).padStart(2, '0')}
  </span>
);

const ActionStepContent = ({ step }: { step: ActionStep }) => (
  <div className="flex-1">
    <p className="text-sm text-gray-800 mb-1">{step.description}</p>
    {step.command && (
      <ActionStepCommand command={step.command} />
    )}
    <ActionStepOutcome expectedOutcome={step.expected_outcome} />
  </div>
);

const ActionStepCommand = ({ command }: { command: string }) => (
  <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono block mb-1">
    {command}
  </code>
);

const ActionStepOutcome = ({ expectedOutcome }: { expectedOutcome: string }) => (
  <p className="text-xs text-gray-600 italic">{expectedOutcome}</p>
);