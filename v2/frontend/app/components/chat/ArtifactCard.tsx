'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card';
import { JsonTreeView } from './JsonTreeView';
import { Artifact } from '@/app/types';

interface ArtifactCardProps {
  artifact: Artifact;
}

export const ArtifactCard: React.FC<ArtifactCardProps> = ({ artifact }) => {
  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>{artifact.type}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{artifact.content}</p>
        <JsonTreeView data={artifact.data} />
      </CardContent>
    </Card>
  );
};