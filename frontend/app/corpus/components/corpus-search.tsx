import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Search } from 'lucide-react';

export const CorpusSearch = () => {
  return (
    <Card>
      <CardHeader>
        <SearchHeader />
      </CardHeader>
      <CardContent className="space-y-4">
        <SearchFilters />
        <SearchActions />
        <SearchHelp />
      </CardContent>
    </Card>
  );
};

const SearchHeader = () => {
  return (
    <>
      <CardTitle>Advanced Search</CardTitle>
      <CardDescription>Search across all corpus data with advanced filters</CardDescription>
    </>
  );
};

const SearchFilters = () => {
  return (
    <div className="grid grid-cols-2 gap-4">
      <SearchQueryField />
      <DataTypeField />
      <DateRangeField />
      <OwnerField />
    </div>
  );
};

const SearchQueryField = () => {
  return (
    <div>
      <Label htmlFor="search-query">Search Query</Label>
      <Input id="search-query" placeholder="Enter search terms..." />
    </div>
  );
};

const DataTypeField = () => {
  return (
    <div>
      <Label htmlFor="search-type">Data Type</Label>
      <Select>
        <SelectTrigger id="search-type">
          <SelectValue placeholder="All types" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Types</SelectItem>
          <SelectItem value="text">Text</SelectItem>
          <SelectItem value="embeddings">Embeddings</SelectItem>
          <SelectItem value="metadata">Metadata</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const DateRangeField = () => {
  return (
    <div>
      <Label htmlFor="date-range">Date Range</Label>
      <Select>
        <SelectTrigger id="date-range">
          <SelectValue placeholder="Last 30 days" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="7">Last 7 days</SelectItem>
          <SelectItem value="30">Last 30 days</SelectItem>
          <SelectItem value="90">Last 90 days</SelectItem>
          <SelectItem value="365">Last year</SelectItem>
          <SelectItem value="all">All time</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const OwnerField = () => {
  return (
    <div>
      <Label htmlFor="owner">Owner</Label>
      <Select>
        <SelectTrigger id="owner">
          <SelectValue placeholder="All owners" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Owners</SelectItem>
          <SelectItem value="me">My Data</SelectItem>
          <SelectItem value="team">Team Data</SelectItem>
          <SelectItem value="system">System Data</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
};

const SearchActions = () => {
  return (
    <div className="flex gap-4">
      <Button>
        <Search className="mr-2 h-4 w-4" />
        Search
      </Button>
      <Button variant="outline">Reset Filters</Button>
    </div>
  );
};

const SearchHelp = () => {
  return (
    <Alert>
      <AlertDescription>
        Use advanced operators: AND, OR, NOT, &quot;exact phrase&quot;, wildcard*
      </AlertDescription>
    </Alert>
  );
};