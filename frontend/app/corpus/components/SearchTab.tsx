'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search } from 'lucide-react';

const SearchField: React.FC<{
  id: string;
  label: string;
  placeholder: string;
}> = ({ id, label, placeholder }) => (
  <div>
    <Label htmlFor={id}>{label}</Label>
    <Input id={id} placeholder={placeholder} />
  </div>
);

const SearchSelect: React.FC<{
  id: string;
  label: string;
  placeholder: string;
  options: { value: string; label: string }[];
}> = ({ id, label, placeholder, options }) => (
  <div>
    <Label htmlFor={id}>{label}</Label>
    <Select>
      <SelectTrigger id={id}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map(option => (
          <SelectItem key={option.value} value={option.value}>
            {option.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  </div>
);

const dataTypeOptions = [
  { value: 'all', label: 'All Types' },
  { value: 'text', label: 'Text' },
  { value: 'embeddings', label: 'Embeddings' },
  { value: 'metadata', label: 'Metadata' },
];

const dateRangeOptions = [
  { value: '7', label: 'Last 7 days' },
  { value: '30', label: 'Last 30 days' },
  { value: '90', label: 'Last 90 days' },
  { value: '365', label: 'Last year' },
  { value: 'all', label: 'All time' },
];

const ownerOptions = [
  { value: 'all', label: 'All Owners' },
  { value: 'me', label: 'My Data' },
  { value: 'team', label: 'Team Data' },
  { value: 'system', label: 'System Data' },
];

export const SearchTab = () => {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Advanced Search</CardTitle>
        <CardDescription>Search across all corpus data with advanced filters</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <SearchField
            id="search-query"
            label="Search Query"
            placeholder="Enter search terms..."
          />
          <SearchSelect
            id="search-type"
            label="Data Type"
            placeholder="All types"
            options={dataTypeOptions}
          />
          <SearchSelect
            id="date-range"
            label="Date Range"
            placeholder="Last 30 days"
            options={dateRangeOptions}
          />
          <SearchSelect
            id="owner"
            label="Owner"
            placeholder="All owners"
            options={ownerOptions}
          />
        </div>
        <div className="flex gap-4">
          <Button>
            <Search className="mr-2 h-4 w-4" />
            Search
          </Button>
          <Button variant="outline">Reset Filters</Button>
        </div>
        <Alert>
          <AlertDescription>
            Use advanced operators: AND, OR, NOT, &quot;exact phrase&quot;, wildcard*
          </AlertDescription>
        </Alert>
      </CardContent>
    </Card>
  );
};