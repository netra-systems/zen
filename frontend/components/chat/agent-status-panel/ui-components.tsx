import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Eye, ChevronRight } from 'lucide-react';
import { StatusZone, ZoneType, DataPreviewItem, Metrics } from './types';

interface HumorSectionProps {
  currentQuip: string;
}

export const HumorSection: React.FC<HumorSectionProps> = ({ currentQuip }) => (
  <motion.div
    key={currentQuip}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="text-xs text-gray-500 italic text-center py-2 border-b"
  >
    {currentQuip}
  </motion.div>
);

const getZoneTypeLabel = (zoneType: ZoneType): string => {
  switch (zoneType) {
    case 'slow': return '10+ sec';
    case 'medium': return '3-10 sec';
    case 'fast': return '< 3 sec';
  }
};

const ZoneTypeHeader: React.FC<{ zoneType: ZoneType }> = ({ zoneType }) => (
  <div className="flex items-center space-x-2 text-xs text-gray-500">
    <Clock className="w-3 h-3" />
    <span className="uppercase font-semibold">
      {getZoneTypeLabel(zoneType)}
    </span>
  </div>
);

const StatusZoneItem: React.FC<{ zone: StatusZone; index: number }> = ({ zone, index }) => (
  <motion.div
    initial={{ opacity: 0, x: -10 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: index * 0.1 }}
    className="bg-gray-50 rounded-lg p-3 border border-gray-100"
  >
    <div className="flex items-start justify-between">
      <div className="flex items-start space-x-2">
        <div className={`${zone.color} mt-0.5`}>
          {zone.icon}
        </div>
        <div className="flex-1">
          <div className="text-xs text-gray-500 mb-1">{zone.label}</div>
          <div className="text-sm font-medium text-gray-900">
            {zone.content}
          </div>
        </div>
      </div>
      <UpdateIndicator lastUpdate={zone.lastUpdate} />
    </div>
  </motion.div>
);

const UpdateIndicator: React.FC<{ lastUpdate: number }> = ({ lastUpdate }) => (
  <AnimatePresence>
    {Date.now() - lastUpdate < 1000 && (
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0 }}
        className="w-1.5 h-1.5 bg-green-500 rounded-full"
      />
    )}
  </AnimatePresence>
);

interface StatusZoneSectionProps {
  statusZones: StatusZone[];
}

export const StatusZoneSection: React.FC<StatusZoneSectionProps> = ({ statusZones }) => (
  <div className="space-y-3">
    {(['slow', 'medium', 'fast'] as ZoneType[]).map(zoneType => {
      const zones = statusZones.filter(z => z.type === zoneType);
      if (zones.length === 0) return null;

      return (
        <div key={zoneType} className="space-y-2">
          <ZoneTypeHeader zoneType={zoneType} />
          {zones.map((zone, idx) => (
            <StatusZoneItem key={`${zoneType}-${idx}`} zone={zone} index={idx} />
          ))}
        </div>
      );
    })}
  </div>
);

const DataPreviewItem: React.FC<{ item: DataPreviewItem; index: number }> = ({ item, index }) => (
  <div className="mb-2">
    <div className="text-blue-400">#{index + 1}</div>
    {Object.entries(item).map(([key, value]) => (
      <div key={key} className="ml-2">
        <span className="text-gray-500">{key}:</span>{' '}
        <span className="text-green-400">{String(value)}</span>
      </div>
    ))}
  </div>
);

const DataPreviewContent: React.FC<{ dataPreview: DataPreviewItem[] }> = ({ dataPreview }) => (
  <div className="bg-gray-900 rounded-lg p-3 text-xs font-mono text-green-400 max-h-40 overflow-y-auto">
    {dataPreview.slice(0, 3).map((item, idx) => (
      <DataPreviewItem key={idx} item={item} index={idx} />
    ))}
    {dataPreview.length > 3 && (
      <div className="text-gray-500 text-center">
        ... {dataPreview.length - 3} more records
      </div>
    )}
  </div>
);

interface DataPreviewSectionProps {
  dataPreview: DataPreviewItem[];
  expandedPreview: string | null;
  setExpandedPreview: (value: string | null) => void;
}

export const DataPreviewSection: React.FC<DataPreviewSectionProps> = ({
  dataPreview,
  expandedPreview,
  setExpandedPreview
}) => {
  if (dataPreview.length === 0) return null;

  const togglePreview = (): void => {
    setExpandedPreview(expandedPreview ? null : 'data');
  };

  return (
    <div className="mt-4">
      <button
        onClick={togglePreview}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center space-x-2 text-xs text-gray-600 font-semibold">
          <Eye className="w-3 h-3" />
          <span>DATA PREVIEW</span>
        </div>
        <ChevronRight 
          className={`w-3 h-3 transition-transform ${
            expandedPreview === 'data' ? 'rotate-90' : ''
          }`}
        />
      </button>
      
      <AnimatePresence>
        {expandedPreview === 'data' && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-2 overflow-hidden"
          >
            <DataPreviewContent dataPreview={dataPreview} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const getConfidenceColor = (score: number): string => {
  if (score > 0.8) return 'bg-green-500';
  if (score > 0.6) return 'bg-yellow-500';
  return 'bg-red-500';
};

interface ConfidenceIndicatorProps {
  metrics: Metrics;
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({ metrics }) => {
  if (metrics.confidenceScore <= 0) return null;

  return (
    <div className="mt-4 pt-4 border-t">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500">Analysis Confidence</span>
        <span className="font-mono font-semibold text-gray-900">
          {(metrics.confidenceScore * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-1 bg-gray-200 rounded-full h-1.5">
        <motion.div
          className={`h-1.5 rounded-full ${getConfidenceColor(metrics.confidenceScore)}`}
          initial={{ width: 0 }}
          animate={{ width: `${metrics.confidenceScore * 100}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </div>
  );
};