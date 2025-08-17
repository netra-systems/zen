// Completed Agents Section Component  
// Business Value: Agent execution visibility for Performance tier customers

import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Clock } from 'lucide-react';
import { formatDuration } from './slow-layer-utils';

interface CompletedAgent {
  agentName: string;
  iteration?: number;
  duration: number;
  metrics?: Record<string, any>;
}

interface CompletedAgentsSectionProps {
  completedAgents: CompletedAgent[];
}

export const CompletedAgentsSection: React.FC<CompletedAgentsSectionProps> = ({ 
  completedAgents 
}) => {
  if (!completedAgents || completedAgents.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <CompletedAgentsHeader agentCount={completedAgents.length} />
      <CompletedAgentsGrid completedAgents={completedAgents} />
    </motion.div>
  );
};

const CompletedAgentsHeader = ({ agentCount }: { agentCount: number }) => (
  <div className="mb-4 p-3 bg-green-50/50 rounded-lg border border-green-200/50">
    <h3 className="text-sm font-semibold text-gray-700 flex items-center justify-between">
      <div className="flex items-center">
        <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
        Completed Agents
      </div>
      <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
        {agentCount} agent{agentCount !== 1 ? 's' : ''}
      </span>
    </h3>
  </div>
);

const CompletedAgentsGrid = ({ completedAgents }: { completedAgents: CompletedAgent[] }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
    {completedAgents.map((agent, index) => (
      <CompletedAgentCard 
        key={`${agent.agentName}-${index}`}
        agent={agent}
        index={index}
      />
    ))}
  </div>
);

const CompletedAgentCard = ({ agent, index }: { 
  agent: CompletedAgent; 
  index: number; 
}) => (
  <motion.div
    className="rounded-lg p-4 border hover:shadow-lg transition-all duration-200 group"
    style={{
      background: 'rgba(255, 255, 255, 0.95)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255, 255, 255, 0.18)',
      boxShadow: '0 2px 6px 0 rgba(0, 0, 0, 0.05)'
    }}
    whileHover={{ scale: 1.02, y: -2 }}
    transition={{ duration: 0.2 }}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    whileInView={{ transition: { delay: index * 0.1 } }}
  >
    <AgentCardHeader agent={agent} />
    {agent.metrics && Object.keys(agent.metrics).length > 0 && (
      <AgentCardMetrics metrics={agent.metrics} />
    )}
  </motion.div>
);

const AgentCardHeader = ({ agent }: { agent: CompletedAgent }) => (
  <div className="flex items-center justify-between mb-3">
    <div>
      <span className="font-semibold text-sm text-gray-800 group-hover:text-gray-900">
        {agent.agentName}
      </span>
      {agent.iteration && agent.iteration > 1 && (
        <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
          Run #{agent.iteration}
        </span>
      )}
    </div>
    <AgentCardTiming duration={agent.duration} />
  </div>
);

const AgentCardTiming = ({ duration }: { duration: number }) => (
  <div className="text-right">
    <div className="text-xs text-gray-500 flex items-center">
      <Clock className="w-3 h-3 mr-1" />
      {formatDuration(duration)}
    </div>
    <div className="text-xs text-green-600 font-medium mt-0.5">
      ✓ Completed
    </div>
  </div>
);

const AgentCardMetrics = ({ metrics }: { metrics: Record<string, any> }) => (
  <div className="text-xs text-gray-600 space-y-1 border-t border-gray-100 pt-2">
    {Object.entries(metrics).slice(0, 4).map(([key, value]) => (
      <div key={key} className="flex justify-between items-center">
        <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
        <span className="font-mono text-gray-800 bg-gray-50 px-1 py-0.5 rounded">
          {typeof value === 'number' ? value.toLocaleString() : String(value)}
        </span>
      </div>
    ))}
  </div>
);