"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Layers } from 'lucide-react';
import type { ActionPlanItem } from './types';

interface ActionPlanStepperProps {
  actionPlan: ActionPlanItem[];
}

interface StepButtonProps {
  index: number;
  currentStep: number;
  onClick: () => void;
}

const StepButton: React.FC<StepButtonProps> = ({ index, currentStep, onClick }) => (
  <button
    onClick={onClick}
    className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
      index <= currentStep
        ? 'bg-indigo-600 text-white'
        : 'bg-gray-200 text-gray-500'
    }`}
  >
    {index < currentStep ? '✓' : index + 1}
  </button>
);

interface StepContentProps {
  step: ActionPlanItem;
}

const StepContent: React.FC<StepContentProps> = ({ step }) => (
  <div className="ml-4 flex-1 pb-8 border-l-2 border-gray-200 pl-4 -ml-0 last:border-0">
    <h4 className="font-medium text-sm text-gray-900 mb-1">
      {step.title || step.description}
    </h4>
    {step.effort_estimate && (
      <p className="text-xs text-gray-500 mb-2">
        Estimated effort: {step.effort_estimate}
      </p>
    )}
    {step.command && (
      <code className="block bg-gray-100 rounded px-3 py-2 text-xs font-mono mb-2">
        {step.command}
      </code>
    )}
    {step.expected_outcome && (
      <p className="text-xs text-gray-600 italic">
        Expected: {step.expected_outcome}
      </p>
    )}
  </div>
);

interface ActionStepProps {
  step: ActionPlanItem;
  index: number;
  currentStep: number;
  onStepClick: (index: number) => void;
}

const ActionStep: React.FC<ActionStepProps> = ({ step, index, currentStep, onStepClick }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: index * 0.1 }}
    className={`flex items-start ${index <= currentStep ? 'opacity-100' : 'opacity-50'}`}
  >
    <StepButton
      index={index}
      currentStep={currentStep}
      onClick={() => onStepClick(index)}
    />
    <StepContent step={step} />
  </motion.div>
);

export const ActionPlanStepper: React.FC<ActionPlanStepperProps> = ({ actionPlan }) => {
  const [currentStep, setCurrentStep] = useState(0);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-800 flex items-center mb-4">
        <Layers className="w-4 h-4 mr-2 text-orange-600" />
        Implementation Roadmap
      </h3>

      <div className="space-y-4">
        {actionPlan.map((step, index) => (
          <ActionStep
            key={step.id}
            step={step}
            index={index}
            currentStep={currentStep}
            onStepClick={setCurrentStep}
          />
        ))}
      </div>
    </div>
  );
};