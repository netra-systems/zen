'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Trash2 } from 'lucide-react';
import { useWebSocket } from '@/contexts/WebSocketContext';

interface Corpus {
  id: string;
  name: string;
  description: string;
  status: string;
  table_name: string;
}

export default function CorpusAdminPage() {
  const [corpora, setCorpora] = useState<Corpus[]>([]);
  const [newCorpusName, setNewCorpusName] = useState('');
  const [newCorpusDescription, setNewCorpusDescription] = useState('');
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    fetchCorpora();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      // A real implementation would parse the message and update the specific corpus
      fetchCorpora();
    }
  }, [lastMessage]);

  const fetchCorpora = async () => {
    const response = await fetch('/api/corpus');
    const data = await response.json();
    setCorpora(data);
  };

  const createCorpus = async () => {
    await fetch('/api/corpus', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newCorpusName, description: newCorpusDescription }),
    });
    fetchCorpora();
    setNewCorpusName('');
    setNewCorpusDescription('');
  };

  const deleteCorpus = async (id: string) => {
    await fetch(`/api/corpus/${id}`, { method: 'DELETE' });
    fetchCorpora();
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Create New Corpus</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input
            placeholder="Corpus Name"
            value={newCorpusName}
            onChange={(e) => setNewCorpusName(e.target.value)}
          />
          <Input
            placeholder="Corpus Description"
            value={newCorpusDescription}
            onChange={(e) => setNewCorpusDescription(e.target.value)}
          />
          <Button onClick={createCorpus}>Create Corpus</Button>
        </CardContent>
      </Card>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Existing Corpora</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Table Name</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {corpora.map((corpus) => (
                <TableRow key={corpus.id}>
                  <TableCell>{corpus.name}</TableCell>
                  <TableCell>{corpus.description}</TableCell>
                  <TableCell>
                    <Badge>{corpus.status}</Badge>
                  </TableCell>
                  <TableCell>{corpus.table_name}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" onClick={() => deleteCorpus(corpus.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
