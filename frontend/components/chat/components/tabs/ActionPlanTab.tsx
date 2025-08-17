import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface ActionPlanTabProps {
  actionPlanResult?: Array<Record<string, unknown>> | Record<string, unknown>;
}

// Check if action plan exists
const hasActionPlan = (actionPlan?: Array<Record<string, unknown>> | Record<string, unknown>): boolean => {
  if (Array.isArray(actionPlan)) return actionPlan.length > 0;
  return Boolean(actionPlan && Object.keys(actionPlan).length > 0);
};

// Check if action plan is array
const isArrayActionPlan = (actionPlan: Array<Record<string, unknown>> | Record<string, unknown>): actionPlan is Array<Record<string, unknown>> => {
  return Array.isArray(actionPlan);
};

// Format action for display
const formatAction = (action: Record<string, unknown>): string => {
  return JSON.stringify(action);
};

// Format object action plan for display
const formatObjectActionPlan = (actionPlan: Record<string, unknown>): string => {
  return JSON.stringify(actionPlan, null, 2);
};

// Action step component
const ActionStep: React.FC<{
  action: Record<string, unknown>;
  index: number;
}> = ({ action, index }) => (
  <Alert className="border-l-4 border-l-blue-500">
    <AlertCircle className="h-4 w-4" />
    <AlertDescription>
      <div className="font-medium mb-1">Step {index + 1}</div>
      <div className="text-sm text-gray-600">{formatAction(action)}</div>
    </AlertDescription>
  </Alert>
);

// Array action plan component
const ArrayActionPlan: React.FC<{
  actions: Array<Record<string, unknown>>;
}> = ({ actions }) => (
  <div className="space-y-3">
    {actions.map((action, idx) => (
      <ActionStep key={idx} action={action} index={idx} />
    ))}
  </div>
);

// Object action plan component
const ObjectActionPlan: React.FC<{
  actionPlan: Record<string, unknown>;
}> = ({ actionPlan }) => (
  <div className="bg-gray-50 rounded-lg p-4">
    <pre className="text-sm overflow-x-auto">
      {formatObjectActionPlan(actionPlan)}
    </pre>
  </div>
);

// Main ActionPlanTab component
export const ActionPlanTab: React.FC<ActionPlanTabProps> = ({ actionPlanResult }) => {
  if (!hasActionPlan(actionPlanResult)) {
    return (
      <div className="text-center text-gray-500 py-8">
        No action plan available
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-green-600" />
          Implementation Action Plan
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isArrayActionPlan(actionPlanResult!) ? (
          <ArrayActionPlan actions={actionPlanResult} />
        ) : (
          <ObjectActionPlan actionPlan={actionPlanResult!} />
        )}
      </CardContent>
    </Card>
  );
};