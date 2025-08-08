'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { useWebSocket } from '@/contexts/WebSocketContext';

export default function SyntheticDataPage() {
  const [corpusTables, setCorpusTables] = useState<string[]>([]);
  const [selectedCorpus, setSelectedCorpus] = useState<string>('');
  const [numLogs, setNumLogs] = useState<number>(1000);
  const { lastMessage } = useWebSocket();

  useEffect(() => {
    fetchCorpusTables();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      // A real implementation would parse the message and update the status
      console.log(lastMessage);
    }
  }, [lastMessage]);

  const fetchCorpusTables = async () => {
    const response = await fetch('/api/v3/corpus/tables');
    const data = await response.json();
    setCorpusTables(data);
  };

  const generateSyntheticData = async () => {
    await fetch('/api/v3/synthetic-data/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ corpus_id: selectedCorpus, num_logs: numLogs }),
    });
  };

  return (
    <div className="container mx-auto p-4">
      <Card>
        <CardHeader>
          <CardTitle>Generate Synthetic Data</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Select onValueChange={setSelectedCorpus}>
            <SelectTrigger>
              <SelectValue placeholder="Select a corpus" />
            </SelectTrigger>
            <SelectContent>
              {corpusTables.map((table) => (
                <SelectItem key={table} value={table}>
                  {table}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Input
            type="number"
            placeholder="Number of logs to generate"
            value={numLogs}
            onChange={(e) => setNumLogs(parseInt(e.target.value))}
          />
          <Button onClick={generateSyntheticData} disabled={!selectedCorpus}>
            Generate Data
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
