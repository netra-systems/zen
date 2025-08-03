"use client";

import React from 'react';
import { ControlPanel } from './ControlPanel';
import { AnalysisResultView } from './AnalysisResultView';

export const Dashboard = () => (
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
    <div className="lg:col-span-1">
      <ControlPanel />
    </div>
    <div className="lg:col-span-2">
      <AnalysisResultView />
    </div>
  </div>
);
