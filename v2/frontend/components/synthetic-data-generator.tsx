"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

const workloadPatterns = [
  { value: "default", label: "Default Workload" },
  { value: "cost_sensitive", label: "Cost-Sensitive" },
  { value: "latency_sensitive", label: "Latency-Sensitive" },
  { value: "high_error_rate", label: "High Error Rate" },
];

export function SyntheticDataGenerator({ onGenerationComplete }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tables, setTables] = useState<string[]>([]);
  const [generationParams, setGenerationParams] = useState({
    num_traces: 100,
    num_users: 10,
    error_rate: 0.1,
    workload_pattern: "default",
    event_types: "search,login",
    source_table: "",
    destination_table: `default.synthetic_data_${Date.now()}`,
  });

  useEffect(() => {
    const fetchTables = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/generation/clickhouse_tables");
        if (!response.ok) throw new Error("Failed to fetch tables.");
        const data = await response.json();
        setTables(data);
        const latestCorpusTable = localStorage.getItem("latest_corpus_table");
        if (latestCorpusTable && data.includes(latestCorpusTable)) {
          setGenerationParams((prev) => ({ ...prev, source_table: latestCorpusTable }));
        } else if (data.length > 0) {
          setGenerationParams((prev) => ({ ...prev, source_table: data[0] }));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred.");
      }
    };
    fetchTables();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setGenerationParams((prev) => ({ ...prev, [name]: parseFloat(value) }));
  };

  const handleSelectChange = (name: string, value: string) => {
    setGenerationParams((prev) => ({ ...prev, [name]: value }));
  };

  const generateData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("http://localhost:8000/api/generation/synthetic_data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(generationParams),
      });
      if (!response.ok) throw new Error("Failed to generate synthetic data.");
      await response.json();
      onGenerationComplete(generationParams.destination_table);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Generate Synthetic Data</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="num_traces">Number of Traces</Label>
            <Input
              id="num_traces"
              name="num_traces"
              type="number"
              value={generationParams.num_traces}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="num_users">Number of Users</Label>
            <Input
              id="num_users"
              name="num_users"
              type="number"
              value={generationParams.num_users}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="error_rate">Error Rate</Label>
            <Input
              id="error_rate"
              name="error_rate"
              type="number"
              step="0.01"
              value={generationParams.error_rate}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="workload_pattern">Workload Pattern</Label>
            <Select
              onValueChange={(value) => handleSelectChange("workload_pattern", value)}
              defaultValue={generationParams.workload_pattern}
            >
              <SelectTrigger id="workload_pattern">
                <SelectValue placeholder="Select a pattern" />
              </SelectTrigger>
              <SelectContent>
                {workloadPatterns.map((pattern) => (
                  <SelectItem key={pattern.value} value={pattern.value}>
                    {pattern.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="event_types">Event Types (comma-separated)</Label>
            <Input
              id="event_types"
              name="event_types"
              type="text"
              value={generationParams.event_types}
              onChange={handleInputChange}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="source_table">Source Table</Label>
            <Select
              onValueChange={(value) => handleSelectChange("source_table", value)}
              value={generationParams.source_table}
            >
              <SelectTrigger id="source_table">
                <SelectValue placeholder="Select a table" />
              </SelectTrigger>
              <SelectContent>
                {tables.map((table) => (
                  <SelectItem key={table} value={table}>
                    {table}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={generateData} disabled={isLoading} className="w-full">
          {isLoading ? "Generating..." : "Generate Data"}
        </Button>
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}