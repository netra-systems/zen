import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText } from 'lucide-react';
import { ADMIN_TEMPLATES } from './constants';
import { AdminTemplate } from './types';

interface TemplatePanelProps {
  show: boolean;
  onTemplateSelect: (template: string) => void;
}

export const TemplatePanel: React.FC<TemplatePanelProps> = ({
  show,
  onTemplateSelect
}) => {
  const handleTemplateClick = (template: AdminTemplate) => {
    onTemplateSelect(template.template);
  };

  const getPreviewText = (template: string) => {
    return template.split('\n')[0] + '...';
  };

  const renderHeader = () => (
    <div className="flex items-center space-x-2 px-2 py-1 text-xs text-gray-500 mb-1">
      <FileText className="w-3 h-3" />
      <span>Admin Templates</span>
    </div>
  );

  const renderTemplateButton = (template: AdminTemplate) => (
    <button
      key={template.name}
      className="w-full text-left px-3 py-2 rounded-md hover:bg-purple-50 transition-colors group"
      onClick={() => handleTemplateClick(template)}
    >
      <div className="flex items-start space-x-2">
        <div className="mt-0.5 text-purple-600">{template.icon}</div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900 group-hover:text-purple-900">
            {template.name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
            {getPreviewText(template.template)}
          </p>
        </div>
      </div>
    </button>
  );

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="absolute bottom-full mb-2 left-0 right-0 bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden max-h-64 overflow-y-auto"
        >
          <div className="p-2">
            {renderHeader()}
            {ADMIN_TEMPLATES.map(renderTemplateButton)}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};