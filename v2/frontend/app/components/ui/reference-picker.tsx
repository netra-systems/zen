'use client';
import React, { useState, useEffect } from 'react';

import { Reference } from '@/app/types/index';

interface ReferencePickerProps {
  onSelect: (reference: Reference) => void;
}

const ReferencePicker: React.FC<ReferencePickerProps> = ({ onSelect }) => {
  const [references, setReferences] = useState<Reference[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReferences = async () => {
      try {
        const response = await fetch('/api/references');
        const data = await response.json();
        setReferences(data.references);
      } catch (error) {
        console.error('Error fetching references:', error);
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