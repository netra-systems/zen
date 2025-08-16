"use client";

import React from 'react';
import { motion } from 'framer-motion';
import type { AgentTimelineItem } from './types';

interface AgentTimelineProps {
  agents: AgentTimelineItem[];
}

const formatDuration = (duration: number): string => {
  return duration < 1000 
    ? `${duration}ms` 
    : `${(duration / 1000).toFixed(1)}s`;
};

interface TimelineBarProps {
  duration: number;
  maxDuration: number;
  index: number;
}

const TimelineBar: React.FC<TimelineBarProps> = ({ duration, maxDuration, index }) => (
  <div className="flex-1 mx-2">
    <div className="bg-gray-200 rounded-full h-4 relative overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${(duration / maxDuration) * 100}%` }}
        transition={{ duration: 0.5, delay: index * 0.1 }}
        className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
      />
    </div>
  </div>
);

interface AgentRowProps {
  agent: AgentTimelineItem;
  maxDuration: number;
  index: number;
}

const AgentRow: React.FC<AgentRowProps> = ({ agent, maxDuration, index }) => (
  <div className="flex items-center">
    <span className="text-xs text-gray-600 w-32 truncate">
      {agent.agentName}
    </span>
    <TimelineBar
      duration={agent.duration || 0}
      maxDuration={maxDuration}
      index={index}
    />
    <span className="text-xs font-mono text-gray-700 w-16 text-right">
      {formatDuration(agent.duration || 0)}
    </span>
  </div>
);

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ agents }) => {
  if (!agents || agents.length === 0) return null;

  const maxDuration = Math.max(...agents.map(a => a.duration || 0));

  return (
    <div className="bg-gray-50 rounded-xl p-4">
      <h4 className="text-xs font-semibold text-gray-700 mb-3">
        Agent Execution Timeline
      </h4>
      <div className="space-y-2">
        {agents.map((agent, index) => (
          <AgentRow
            key={`${agent.agentName}-${index}`}
            agent={agent}
            maxDuration={maxDuration}
            index={index}
          />
        ))}
      </div>
    </div>
  );
};