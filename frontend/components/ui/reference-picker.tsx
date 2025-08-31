'use client';
import React, { useState, useEffect } from 'react';
import { logger } from '@/lib/logger';

import { ReferenceItem as Reference } from '@/types/Reference';

interface ReferencePickerProps {
  onSelect: (reference: Reference) => void;
}

const ReferencePicker: React.FC<ReferencePickerProps> = ({ onSelect }) => {
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReferences = async () => {
      try {
        const token = localStorage.getItem('jwt_token') || sessionStorage.getItem('jwt_token');
        const response = await fetch('/api/references', {
          headers: {
            ...(token && { 'Authorization': `Bearer ${token}` })
          }
        });
        const data = await response.json();
        setReferences(data.references);
      } catch (error) {
        logger.error('Error fetching references:', error);
      }
      setLoading(false);
    };

    fetchReferences();
  }, []);

  if (loading) {
    return <div>Loading references...</div>;
  }

  return (
    <div className="reference-picker">
      <h3>Select a Reference</h3>
      <ul>
        {references.map((ref) => (
          <li key={ref.id} onClick={() => onSelect(ref)}>
            <strong>{ref.friendly_name}</strong> ({ref.type})
            <p>{ref.description}</p>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ReferencePicker;