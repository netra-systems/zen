'use client';

import { Artifact } from '../types';

interface ArtifactRendererProps {
  artifact: Artifact;
}

export function ArtifactRenderer({ artifact }: ArtifactRendererProps) {
  switch (artifact.type) {
    case 'table':
      return <div>Table component</div>;
    case 'chart':
      return <div>Chart component</div>;
    case 'code':
      return <pre className="bg-gray-100 p-2 rounded">{JSON.stringify(artifact.data, null, 2)}</pre>;
    default:
      return null;
  }
}
